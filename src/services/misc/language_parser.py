from langdetect import detect
from models.enums.language import Language

class LanguageParser:
  def get_language(self, string: str) -> Language:
    lang_code = detect(string)
    return self._map_lang_code(lang_code)

  def _map_lang_code(self, code: str) -> Language:
    if code == "en":
      return Language.ENGLISH
    input("Found a nonenglish -- do we return???")
    if code == "es":
      return Language.SPANISH
    elif code == "fr":
      return Language.FRENCH
    else:
      return Language.UNKNOWN
