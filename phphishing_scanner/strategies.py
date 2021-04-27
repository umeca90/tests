from abc import ABC, abstractmethod
import homoglyphs as hg
import chardet
import string

URL_RESERVED_CHARS = "$|.+!*'(),"


class Strategy(ABC):
    """
    Базовый класс стратегии определяющий общий интерфейс.
    """

    def __init__(self, domain_string: str, phishing_domains: list) -> None:
        self.domain_string = domain_string.lower()
        self.phishing_domains = phishing_domains

    @abstractmethod
    def perform_strategy(self) -> None:
        pass


class HomoglyphGeneratorStrategy(Strategy):
    """
    Класс-стратегия отвечает за подстановку символа, схожего по написанию и
    генерацию доменов, на основе этой подстановки.
    """

    def __init__(self, domain_string: str, phishing_domains: list) -> None:
        super(HomoglyphGeneratorStrategy, self).__init__(domain_string, phishing_domains)
        self.glyphs_generator = hg.Homoglyphs(languages={'en'}, categories=('COMMON', 'LATIN'))
        self.glyphs_dict = dict()

    def perform_strategy(self) -> None:
        possible_glyphs = list()
        for char in self.domain_string:
            possible_glyphs.extend(self._generate_glyphs(char))
        self._generate_strings_with_homoglyphs(possible_glyphs)

    def _generate_glyphs(self, char: str) -> list:
        """
        Функция получает на вход букву и генерирует возможные ascii символы homoglyph
        :param char: str буква
        :return ascii_glyphs: список возможных homoglyph ascii.
        """
        possible_glyphs = self.glyphs_generator.get_combinations(char.lower())
        possible_glyphs.extend(self.glyphs_generator.get_combinations(char.upper()))
        filtered_glyphs = list(filter(lambda gl: gl not in URL_RESERVED_CHARS, possible_glyphs))
        ascii_glyphs = list(
            filter(lambda gl: chardet.detect(str.encode(gl))['encoding'] == 'ascii' and gl.lower() != char,
                   filtered_glyphs))

        for gl in ascii_glyphs:
            self.glyphs_dict[gl] = char
        return ascii_glyphs

    def _generate_strings_with_homoglyphs(self, possible_glyphs: list, words=None) -> None:
        """
        Функция принимает на вход возможные символы homoglyph и
         слова для генерации новых слов с подстановкой этих символов
         и последующим сохранением в переменную self.phishing_domains.
         :param possible_glyphs: список возможных символов homoglyph
        """
        if not words:
            words = [self.domain_string]
        replaced_words = []
        chars_to_replace = [value for value in self.glyphs_dict.values()]
        if not self._any_char_to_replace(words, chars_to_replace):
            return
        for word in words:
            for glyph in possible_glyphs:
                char = self.glyphs_dict[glyph]
                if char in word:
                    index = word.index(char)
                    new_word = list(word)
                    new_word[index] = glyph
                    replaced_words.append(''.join(new_word).lower())
        self.phishing_domains.extend(replaced_words)
        self._generate_strings_with_homoglyphs(possible_glyphs, replaced_words)

    def _any_char_to_replace(self, words: list, chars: list) -> bool:
        """
        Функция проверяет, есть ли в слове переданные в параметре символы.
        """
        for word in words:
            return any(char in word for char in chars)


class AdditionalSymbolStrategy(Strategy):
    """
    Класс-стратегия отвечает за генерацию доменов путем подстановки символа в конце доменной строки.
    """

    def __init__(self, domain_string: str, phishing_domains: list) -> None:
        super(AdditionalSymbolStrategy, self).__init__(domain_string, phishing_domains)

    def perform_strategy(self) -> None:
        self.add_symbol_to_end()

    def add_symbol_to_end(self) -> None:
        alphabet = list(string.ascii_lowercase)
        for letter in alphabet:
            self.phishing_domains.append(self.domain_string + letter)


class AddSubDomainStrategy(Strategy):
    """
    Класс-стратегия отвечает за генерацию под доменов в строке домена путем подстановки символа точка.
    """

    def __init__(self, domain_string: str, phishing_domains: list) -> None:
        super(AddSubDomainStrategy, self).__init__(domain_string, phishing_domains)

    def perform_strategy(self) -> None:
        self.add_sub_domain()

    def add_sub_domain(self) -> None:
        """
        Функция поочередно подставляет точку между символами в строке для генерации под доменов
         и добавляет результат в переменную self.phishing_domains
        """
        for i in range(1, len(self.domain_string)):
            first_part = self.domain_string[:i]
            second_part = self.domain_string[i:]
            if '-' in first_part[-1] or '-' in second_part[0]:
                continue
            else:
                word = self.domain_string[:i] + '.' + self.domain_string[i:]
            self.phishing_domains.append(word)


class RemoveSymbolStrategy(Strategy):
    """
    Класс-стратегия отвечает за удаление одного символа в конце доменного имени.
    """

    def __init__(self, domain_string, phishing_domains) -> None:
        super(RemoveSymbolStrategy, self).__init__(domain_string, phishing_domains)

    def perform_strategy(self) -> None:
        self.remove_one_symbol()

    def remove_one_symbol(self) -> None:
        """
        Функция поочередно удаляет по одному символу в строке и добавляет результат в переменную self.phishing_domains
        """
        for i in range(len(self.domain_string)):
            word = self.domain_string[:i] + self.domain_string[i + 1:]
            self.phishing_domains.append(word)
