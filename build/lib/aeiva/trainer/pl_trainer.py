import pytorch_lightning as pl
import torch
import torch.nn as nn
import inspect
import time


class LightningTrainer(pl.LightningModule):
    def __init__(self, model, tokenizer, config):
        super().__init__()
        self.model = model
        self.tokenizer = tokenizer
        self.config = config

    def forward(self, batch):
        outputs = self.model(batch)
        return outputs

    def training_step(self, batch, batch_idx):
        outputs = self(batch)
        loss = outputs.loss
        return {"loss": loss}

    def validation_step(self, batch, batch_idx):
        outputs = self(batch)
        loss = outputs.loss
        return {"loss": loss}
    
    def test_step(self, batch, batch_idx):
        outputs = self(batch)
        loss = outputs.loss
        return {"loss": loss}

    def configure_optimizers(self):
        """
        Function to prepare the optimizer and learning rate scheduler for model training.
        This function separates model parameters into two categories: parameters that will experience weight decay, 
        and those that will not (e.g., bias and layernorm weights). 

        Returns:
            Tuple[Optimizer, Scheduler]: Tuple containing the optimizer and learning rate scheduler.
        """

        # List of module types that will be subjected to weight decay.
        whitelist_weight_modules = (torch.nn.Linear, ) 

        # List of module types that will not be subjected to weight decay.
        blacklist_weight_modules = (torch.nn.LayerNorm, torch.nn.Embedding)

        # Parameter sets for decay and no decay.
        decay = set()
        no_decay = set()

        # Populate the decay and no_decay sets. 
        # Loop over all modules to get module name (mn) and module (m).
        # !!!! revise later.
        # for mn, m in self.model.named_modules():
        #     for pn, p in m.named_parameters():
        #         fpn = '%s.%s' % (mn, pn) if mn else pn 
                
        #         if 'bias' in pn:
        #             no_decay.add(fpn)
        #         elif 'weight' in pn:
        #             decay.add(fpn)
        
        param_dict = {pn: p for pn, p in self.model.named_parameters()}

        for mn, m in self.model.named_modules():
            for pn, p in m.named_parameters():
                fpn = '%s.%s' % (mn, pn) if mn else pn  # full param name
                # random note: because named_modules and named_parameters are recursive
                # we will see the same tensors p many many times. but doing it this way
                # allows us to know which parent module any tensor p belongs to...
                # Adding new condition to check for the 'class_embedding' and 'logit_scale' parameters
                if pn.endswith('bias') or 'class_embedding' in pn or 'logit_scale' in pn:
                    no_decay.add(fpn)
                elif pn.endswith('weight') and isinstance(m, blacklist_weight_modules):
                    no_decay.add(fpn)
        for pn, p in param_dict.items():
            if pn not in no_decay:
                decay.add(pn)


        # # After this loop, print out all parameters in the intersection of decay and no_decay:
        # print("decay: ", decay)
        # print("no_decay: ", no_decay)
        # print("intersection: ", decay.intersection(no_decay))
        
        # print("difference: ", param_dict.keys() - (decay | no_decay))


        # # 'lm_head.weight' is tied to 'model.embed_tokens.weight', so it should not be decayed. 
        # # This ensures that the same tensor is not optimized in different ways.
        # decay.remove('llm.lm_head.weight')

        # Validate that we considered every parameter.
        param_dict = {pn: p for pn, p in self.model.named_parameters()}
        assert len(decay & no_decay) == 0, "Some parameters are in both decay and no_decay sets!"
        assert len(param_dict.keys() - (decay | no_decay)) == 0, "Some parameters are in neither decay nor no_decay sets!"

        # Create the PyTorch optimizer object.
        optim_groups = [
            {"params": [param_dict[pn] for pn in sorted(list(decay))], "weight_decay": self.config.weight_decay},
            {"params": [param_dict[pn] for pn in sorted(list(no_decay))], "weight_decay": 0.0},
        ]
        # new PyTorch nightly has a new 'fused' option for AdamW that is much faster
        use_fused = (self.config.device == 'cuda') and (
            'fused' in inspect.signature(torch.optim.AdamW).parameters)
        print(f"using fused AdamW: {use_fused}")
        extra_args = dict(fused=True) if use_fused else dict()
        optimizer = torch.optim.AdamW(
            optim_groups, lr=self.config.learning_rate, betas=(self.config.adam_beta1, self.config.adam_beta2), **extra_args)

        # Prepare learning rate scheduler.
        total_steps = self.config.max_steps
        pct_start = self.config.warmup_steps / total_steps
        final_div_factor = self.config.learning_rate / self.config.min_lr

        scheduler = {
            'scheduler': torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=self.config.learning_rate,
                total_steps=total_steps,
                pct_start=pct_start,
                final_div_factor=final_div_factor,
                div_factor=1.0,  # No additional scaling for the initial learning rate
                anneal_strategy='cos',  # Use cosine annealing
                cycle_momentum=False,  # Disable momentum cycling
            ),
            'interval': 'step',
            'frequency': 1
        }

        return [optimizer], [scheduler]


    def get_num_params(self, non_embedding=True):
        """
        Return the number of parameters in the model.
        For non-embedding count (default), the position embeddings get subtracted.
        The token embeddings would too, except due to the parameter sharing these
        params are actually used as weights in the final layer, so we include them.
        """
        n_params = sum(p.numel() for p in self.model.parameters())
        if non_embedding:
            embedding_params = sum(p.numel() for m in self.model.modules() if isinstance(m, nn.Embedding) for p in m.parameters())
            n_params -= embedding_params
        return n_params

    def estimate_mfu(self, fwdbwd_per_iter, dt):
        """ estimate model flops utilization (MFU) in units of A100 bfloat16 peak FLOPS """
        # first estimate the number of flops we do per iteration.
        # see PaLM paper Appendix B as ref: https://arxiv.org/abs/2204.02311
        N = self.get_num_params()
        cfg = self.config
        L, H, Q, T = cfg.n_layer, cfg.n_head, cfg.n_embd//cfg.n_head, cfg.block_size
        flops_per_token = 6*N + 12*L*H*Q*T
        flops_per_fwdbwd = flops_per_token * T
        flops_per_iter = flops_per_fwdbwd * fwdbwd_per_iter
        # express our flops throughput as ratio of A100 bfloat16 peak flops
        flops_achieved = flops_per_iter * (1.0/dt)  # per second
        flops_promised = 312e12  # A100 GPU bfloat16 peak flops is 312 TFLOPS
        mfu = flops_achieved / flops_promised
        return mfu



class LoggingCallback(pl.Callback):
    def __init__(self, log_every_n_steps, accumulate_grad_batches):
        super().__init__()
        self.log_every_n_steps = log_every_n_steps
        self.accumulate_grad_batches = accumulate_grad_batches
        self.running_mfu = -1.0
        self.local_iter_num = 0
        self.t0 = time.time()

    def on_train_batch_end(self, trainer, pl_module, outputs, *args, **kwargs):
        # Access the loss from the outputs
        loss = outputs["loss"]
        
        # Log the train loss
        pl_module.log("train_loss", loss, on_step=True, on_epoch=True, prog_bar=True, logger=True)
        
        # Log the learning rate
        lr = pl_module.trainer.optimizers[0].param_groups[0]["lr"]
        pl_module.log("lr", lr, on_step=True, on_epoch=False, logger=True)

        # Log the mfu
        if trainer.global_step % self.log_every_n_steps == 0:
            # calculate dt
            t1 = time.time()
            dt = t1 - self.t0
            self.t0 = t1

            if self.local_iter_num >= 5:  # let the training loop settle a bit
                mfu = pl_module.estimate_mfu(
                    pl_module.config.batch_size * self.accumulate_grad_batches, dt)
                self.running_mfu = mfu if self.running_mfu == -1.0 else 0.9 * self.running_mfu + 0.1 * mfu
            
            pl_module.log("mfu", self.running_mfu, on_step=True, on_epoch=False, prog_bar=True, logger=True)
            self.local_iter_num += 1

    def on_validation_batch_end(self, trainer, pl_module, outputs, *args, **kwargs):
        loss = outputs["loss"]
        pl_module.log('val_loss', loss, on_step=True, on_epoch=True, prog_bar=True, logger=True)

    def on_test_batch_end(self, trainer, pl_module, outputs, *args, **kwargs):
        loss = outputs["loss"]
        pl_module.log('test_loss', loss, on_step=True, on_epoch=True, prog_bar=True, logger=True)
