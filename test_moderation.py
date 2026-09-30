import time
from core.classifier import ToxicityClassifier
from core.translator import ChatTranslator

if __name__ == "__main__":
    classifier = ToxicityClassifier()

    test_samples = [
        ("Bhai mast move chala tune!", "en"),                  # Clean Hinglish praise
        ("You are such a complete noob, uninstall game", "hi"), # Toxic trash talk
        ("Tere ghar aake jaan se maar dunga", "en"),           # Severe threat / harassment
        ("Gandu sala nikal yahan se", "en"),                   # Direct slur / harassment
    ]

    print("\n--- RUNNING MODEL VERIFICATION ---\n")
    for text, target_lang in test_samples:
        result = classifier.analyze(text)
        translated = ChatTranslator.translate(text, target_lang)

        print(f"Input Text   : {text}")
        print(f"Verdict      : {result['verdict'].value}")
        print(f"Scores       : {result['scores']}")
        print(f"Translated   : {translated}")
        print("-" * 50)
        time.sleep(1)  # small delay so Google doesn't rate-limit