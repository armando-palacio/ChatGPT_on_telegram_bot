import os
import azure.cognitiveservices.speech as speechsdk

def set_speech_config(subscription, region):
    global speech_config
    speech_config = speechsdk.SpeechConfig(subscription=subscription, region=region)


def text_to_speech(text, language="es-ES", filename="output.wav"):
    speech_config.speech_synthesis_language = language
    audio_config = speechsdk.audio.AudioOutputConfig(filename=filename, use_default_speaker=False)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    return synthesizer.speak_text_async(text).get()


def speech_to_text(filename, language='es-ES'):
    audio_config = speechsdk.audio.AudioConfig(filename=filename)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config, language=language)
    result = speech_recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return result.no_match_details
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        return cancellation_details.reason

