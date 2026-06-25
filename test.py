import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf

device = "cuda:0" if torch.cuda.is_available() else "cpu"
model = ParlerTTSForConditionalGeneration.from_pretrained("parler-tts/parler-tts-large-v1").to(device)
tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler-tts-large-v1")

text = "Hello Natnael, welcome to EthioChatbot!"
description = "A warm male voice with moderate speed and clear pronunciation."

input_ids = tokenizer(description, return_tensors="pt").input_ids.to(device)
prompt_ids = tokenizer(text, return_tensors="pt").input_ids.to(device)

generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_ids)
audio_arr = generation.cpu().numpy().squeeze()

sf.write("ethiochatbot_tts.wav", audio_arr, model.config.sampling_rate)

