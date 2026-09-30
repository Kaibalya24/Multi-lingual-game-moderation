from deep_translator import GoogleTranslator

class ChatTranslator:
    @staticmethod
    def translate(text: str, target_lang: str) -> str:
        if not text or not text.strip() or target_lang in ("auto", "same"):
            return text

        lang_code = target_lang.lower().strip()
        try:
            # Fast Google Translation
            res = GoogleTranslator(source="auto", target=lang_code).translate(text)
            if res and res.strip():
                return res
        except Exception as e:
            print(f"[Translation Notice] Using original text ({e})")

        return text