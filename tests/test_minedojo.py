import pytest

minedojo = pytest.importorskip("minedojo")


def test_minedojo_smoke():
    env = minedojo.make(
        task_id="combat_spider_plains_leather_armors_diamond_sword_shield",
        image_size=(288, 512),
        world_seed=123,
        seed=42,
    )

    env.reset()
    for _ in range(20):
        env.step(env.action_space.no_op())
    env.close()


if __name__ == "__main__":
    test_minedojo_smoke()
