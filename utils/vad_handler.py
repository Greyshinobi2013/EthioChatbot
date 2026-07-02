import webrtcvad

vad = webrtcvad.Vad(1)

def set_vad_level(level):
    global vad
    vad = webrtcvad.Vad(level)