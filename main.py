from elevenlabs import ElevenLabs, Voice, VoiceSettings

def genElevenLabs(voiceID, text, speedoftext,elevenlabs_api_key):
    client = ElevenLabs(api_key=elevenlabs_api_key)
    voice_settings = VoiceSettings(speed=speedoftext)
    voice = Voice(voice_id=voiceID, settings=voice_settings)
    audio = client.generate(text=text, voice=voice)
    with open("output.mp3", "wb") as f:
    f.write(audio)



# basic voice generation test