import gradio as gr
import sounddevice as sd
import soundfile as sf
import cv2

def record_audio(duration=5):
    rec = sd.rec(int(duration * 44100), samplerate=44100, channels=2)
    sd.wait()
    filename = "output.wav"
    sf.write(filename, rec, 44100)
    return filename

def record_video(duration=5):
    cap = cv2.VideoCapture(0)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))
    start_time = cv2.getTickCount()
    while (cv2.getTickCount() - start_time) / cv2.getTickFrequency() < duration:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        cv2.imshow('frame', frame)
        if cv2.waitKey(1) == ord('q'):
            break
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    return 'output.avi'

audio_button = gr.Button("Record Audio", type="default", onclick=record_audio)
video_button = gr.Button("Record Video", type="default", onclick=record_video)

iface = gr.Interface(
    fn=None,
    inputs=None,
    outputs=None,
    title="Aeiva Chatbot",
    layout="blocks",
    css=None,
    server_name=None,
    server_port=None,
)

iface.add_blocks(
    gr.Row(
        gr.Column(
            gr.Row(
                gr.Image(type="pil"),
                gr.Video(),
                gr.Audio(),
            ),
            audio_button,
            video_button,
            gr.Audio(source="microphone", streaming=True, interactive=True),
            scale=0.5,
        ),
        gr.Column(
            gr.Row(
                gr.Chatbot([], elem_id="chatbot").style(height=750),
            ),
            gr.Row(
                gr.Column(
                    gr.Textbox(
                        show_label=False,
                        placeholder="Enter text and press enter, or upload an image",
                    ).style(container=False),
                    gr.UploadButton("📁", file_types=["image", "video", "audio"]),
                    scale=0.8,
                ),
                gr.Column(
                    gr.Button("Submit", type="default"),
                    scale=0.2,
                    min_width=0,
                ),
            ),
            scale=0.5,
        ),
    ),
)

iface.launch()
