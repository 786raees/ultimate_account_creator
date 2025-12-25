"""
Country Profiles for Fingerprint Matching
==========================================

Maps phone country codes to matching browser fingerprint data.
This ensures the fingerprint (timezone, locale, language) matches
the phone number's country for consistent profiles.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import random

from src.utils.logger import get_logger


@dataclass
class CountryProfile:
    """
    Profile data for a specific country.

    Contains all the information needed to create a consistent
    browser fingerprint that matches the country.
    """

    country_code: str  # Phone country code (e.g., "380" for Ukraine)
    country_name: str
    iso_code: str  # ISO 3166-1 alpha-2 (e.g., "UA")

    # Locale settings
    locales: List[str]  # Primary locales (e.g., ["uk-UA", "ru-UA"])
    accept_languages: List[str]  # Accept-Language headers

    # Timezone settings
    timezones: List[str]  # Common timezones in the country

    currency: str  # Currency code (e.g., "UAH")

    def get_random_locale(self) -> str:
        """Get a random locale from available options."""
        return random.choice(self.locales)

    def get_random_timezone(self) -> str:
        """Get a random timezone from available options."""
        return random.choice(self.timezones)

    def get_random_accept_language(self) -> str:
        """Get a random Accept-Language header."""
        return random.choice(self.accept_languages)


# Comprehensive country profiles mapped by phone country code
COUNTRY_PROFILES: Dict[str, CountryProfile] = {
    # Ukraine (+380)
    "380": CountryProfile(
        country_code="380",
        country_name="Ukraine",
        iso_code="UA",
        locales=["uk-UA", "ru-UA", "en-UA"],
        accept_languages=[
            "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
            "ru-UA,ru;q=0.9,uk;q=0.8,en-US;q=0.7,en;q=0.6",
            "uk,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Kiev", "Europe/Kyiv"],
        currency="UAH",
    ),

    # United States (+1)
    "1": CountryProfile(
        country_code="1",
        country_name="United States",
        iso_code="US",
        locales=["en-US"],
        accept_languages=[
            "en-US,en;q=0.9",
            "en-US,en;q=0.9,es;q=0.8",
        ],
        timezones=[
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "America/Phoenix",
        ],
        currency="USD",
    ),

    # United Kingdom (+44)
    "44": CountryProfile(
        country_code="44",
        country_name="United Kingdom",
        iso_code="GB",
        locales=["en-GB"],
        accept_languages=[
            "en-GB,en;q=0.9",
            "en-GB,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/London"],
        currency="GBP",
    ),

    # Germany (+49)
    "49": CountryProfile(
        country_code="49",
        country_name="Germany",
        iso_code="DE",
        locales=["de-DE", "en-DE"],
        accept_languages=[
            "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "de,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Berlin"],
        currency="EUR",
    ),

    # France (+33)
    "33": CountryProfile(
        country_code="33",
        country_name="France",
        iso_code="FR",
        locales=["fr-FR", "en-FR"],
        accept_languages=[
            "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "fr,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Paris"],
        currency="EUR",
    ),

    # Spain (+34)
    "34": CountryProfile(
        country_code="34",
        country_name="Spain",
        iso_code="ES",
        locales=["es-ES", "ca-ES", "en-ES"],
        accept_languages=[
            "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "es,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Madrid"],
        currency="EUR",
    ),

    # Italy (+39)
    "39": CountryProfile(
        country_code="39",
        country_name="Italy",
        iso_code="IT",
        locales=["it-IT", "en-IT"],
        accept_languages=[
            "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "it,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Rome"],
        currency="EUR",
    ),

    # Netherlands (+31)
    "31": CountryProfile(
        country_code="31",
        country_name="Netherlands",
        iso_code="NL",
        locales=["nl-NL", "en-NL"],
        accept_languages=[
            "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "nl,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Amsterdam"],
        currency="EUR",
    ),

    # Poland (+48)
    "48": CountryProfile(
        country_code="48",
        country_name="Poland",
        iso_code="PL",
        locales=["pl-PL", "en-PL"],
        accept_languages=[
            "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
            "pl,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Warsaw"],
        currency="PLN",
    ),

    # Russia (+7)
    "7": CountryProfile(
        country_code="7",
        country_name="Russia",
        iso_code="RU",
        locales=["ru-RU", "en-RU"],
        accept_languages=[
            "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "ru,en-US;q=0.9,en;q=0.8",
        ],
        timezones=[
            "Europe/Moscow",
            "Europe/Samara",
            "Asia/Yekaterinburg",
            "Asia/Novosibirsk",
        ],
        currency="RUB",
    ),

    # Brazil (+55)
    "55": CountryProfile(
        country_code="55",
        country_name="Brazil",
        iso_code="BR",
        locales=["pt-BR", "en-BR"],
        accept_languages=[
            "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "pt,en-US;q=0.9,en;q=0.8",
        ],
        timezones=[
            "America/Sao_Paulo",
            "America/Rio_Branco",
            "America/Manaus",
        ],
        currency="BRL",
    ),

    # Canada (+1 - same as US, but with different locales)
    # Note: Canada uses +1, need to differentiate by area code or default to US

    # Australia (+61)
    "61": CountryProfile(
        country_code="61",
        country_name="Australia",
        iso_code="AU",
        locales=["en-AU"],
        accept_languages=[
            "en-AU,en;q=0.9",
            "en-AU,en-US;q=0.9,en;q=0.8",
        ],
        timezones=[
            "Australia/Sydney",
            "Australia/Melbourne",
            "Australia/Brisbane",
            "Australia/Perth",
        ],
        currency="AUD",
    ),

    # India (+91)
    "91": CountryProfile(
        country_code="91",
        country_name="India",
        iso_code="IN",
        locales=["en-IN", "hi-IN"],
        accept_languages=[
            "en-IN,en;q=0.9,hi;q=0.8",
            "en-IN,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Kolkata"],
        currency="INR",
    ),

    # Japan (+81)
    "81": CountryProfile(
        country_code="81",
        country_name="Japan",
        iso_code="JP",
        locales=["ja-JP", "en-JP"],
        accept_languages=[
            "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
            "ja,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Tokyo"],
        currency="JPY",
    ),

    # South Korea (+82)
    "82": CountryProfile(
        country_code="82",
        country_name="South Korea",
        iso_code="KR",
        locales=["ko-KR", "en-KR"],
        accept_languages=[
            "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "ko,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Seoul"],
        currency="KRW",
    ),

    # China (+86)
    "86": CountryProfile(
        country_code="86",
        country_name="China",
        iso_code="CN",
        locales=["zh-CN", "en-CN"],
        accept_languages=[
            "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "zh,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Shanghai"],
        currency="CNY",
    ),

    # Mexico (+52)
    "52": CountryProfile(
        country_code="52",
        country_name="Mexico",
        iso_code="MX",
        locales=["es-MX", "en-MX"],
        accept_languages=[
            "es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "es,en-US;q=0.9,en;q=0.8",
        ],
        timezones=[
            "America/Mexico_City",
            "America/Cancun",
            "America/Tijuana",
        ],
        currency="MXN",
    ),

    # Turkey (+90)
    "90": CountryProfile(
        country_code="90",
        country_name="Turkey",
        iso_code="TR",
        locales=["tr-TR", "en-TR"],
        accept_languages=[
            "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "tr,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Istanbul"],
        currency="TRY",
    ),

    # Sweden (+46)
    "46": CountryProfile(
        country_code="46",
        country_name="Sweden",
        iso_code="SE",
        locales=["sv-SE", "en-SE"],
        accept_languages=[
            "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7",
            "sv,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Stockholm"],
        currency="SEK",
    ),

    # Norway (+47)
    "47": CountryProfile(
        country_code="47",
        country_name="Norway",
        iso_code="NO",
        locales=["no-NO", "nb-NO", "en-NO"],
        accept_languages=[
            "no-NO,no;q=0.9,en-US;q=0.8,en;q=0.7",
            "nb,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Oslo"],
        currency="NOK",
    ),

    # Denmark (+45)
    "45": CountryProfile(
        country_code="45",
        country_name="Denmark",
        iso_code="DK",
        locales=["da-DK", "en-DK"],
        accept_languages=[
            "da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7",
            "da,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Copenhagen"],
        currency="DKK",
    ),

    # Finland (+358)
    "358": CountryProfile(
        country_code="358",
        country_name="Finland",
        iso_code="FI",
        locales=["fi-FI", "sv-FI", "en-FI"],
        accept_languages=[
            "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7",
            "fi,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Helsinki"],
        currency="EUR",
    ),

    # Switzerland (+41)
    "41": CountryProfile(
        country_code="41",
        country_name="Switzerland",
        iso_code="CH",
        locales=["de-CH", "fr-CH", "it-CH", "en-CH"],
        accept_languages=[
            "de-CH,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "fr-CH,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        ],
        timezones=["Europe/Zurich"],
        currency="CHF",
    ),

    # Austria (+43)
    "43": CountryProfile(
        country_code="43",
        country_name="Austria",
        iso_code="AT",
        locales=["de-AT", "en-AT"],
        accept_languages=[
            "de-AT,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "de,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Vienna"],
        currency="EUR",
    ),

    # Belgium (+32)
    "32": CountryProfile(
        country_code="32",
        country_name="Belgium",
        iso_code="BE",
        locales=["nl-BE", "fr-BE", "de-BE", "en-BE"],
        accept_languages=[
            "nl-BE,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "fr-BE,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        ],
        timezones=["Europe/Brussels"],
        currency="EUR",
    ),

    # Portugal (+351)
    "351": CountryProfile(
        country_code="351",
        country_name="Portugal",
        iso_code="PT",
        locales=["pt-PT", "en-PT"],
        accept_languages=[
            "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "pt,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Lisbon"],
        currency="EUR",
    ),

    # Greece (+30)
    "30": CountryProfile(
        country_code="30",
        country_name="Greece",
        iso_code="GR",
        locales=["el-GR", "en-GR"],
        accept_languages=[
            "el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7",
            "el,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Athens"],
        currency="EUR",
    ),

    # Czech Republic (+420)
    "420": CountryProfile(
        country_code="420",
        country_name="Czech Republic",
        iso_code="CZ",
        locales=["cs-CZ", "en-CZ"],
        accept_languages=[
            "cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7",
            "cs,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Prague"],
        currency="CZK",
    ),

    # Romania (+40)
    "40": CountryProfile(
        country_code="40",
        country_name="Romania",
        iso_code="RO",
        locales=["ro-RO", "en-RO"],
        accept_languages=[
            "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
            "ro,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Bucharest"],
        currency="RON",
    ),

    # Hungary (+36)
    "36": CountryProfile(
        country_code="36",
        country_name="Hungary",
        iso_code="HU",
        locales=["hu-HU", "en-HU"],
        accept_languages=[
            "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
            "hu,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Budapest"],
        currency="HUF",
    ),

    # Israel (+972)
    "972": CountryProfile(
        country_code="972",
        country_name="Israel",
        iso_code="IL",
        locales=["he-IL", "en-IL"],
        accept_languages=[
            "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "he,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Jerusalem"],
        currency="ILS",
    ),

    # United Arab Emirates (+971)
    "971": CountryProfile(
        country_code="971",
        country_name="United Arab Emirates",
        iso_code="AE",
        locales=["ar-AE", "en-AE"],
        accept_languages=[
            "ar-AE,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "en-AE,en;q=0.9,ar;q=0.8",
        ],
        timezones=["Asia/Dubai"],
        currency="AED",
    ),

    # Singapore (+65)
    "65": CountryProfile(
        country_code="65",
        country_name="Singapore",
        iso_code="SG",
        locales=["en-SG", "zh-SG"],
        accept_languages=[
            "en-SG,en;q=0.9",
            "en-SG,en-US;q=0.9,en;q=0.8,zh;q=0.7",
        ],
        timezones=["Asia/Singapore"],
        currency="SGD",
    ),

    # Thailand (+66)
    "66": CountryProfile(
        country_code="66",
        country_name="Thailand",
        iso_code="TH",
        locales=["th-TH", "en-TH"],
        accept_languages=[
            "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
            "th,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Bangkok"],
        currency="THB",
    ),

    # Indonesia (+62)
    "62": CountryProfile(
        country_code="62",
        country_name="Indonesia",
        iso_code="ID",
        locales=["id-ID", "en-ID"],
        accept_languages=[
            "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "id,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Jakarta"],
        currency="IDR",
    ),

    # Philippines (+63)
    "63": CountryProfile(
        country_code="63",
        country_name="Philippines",
        iso_code="PH",
        locales=["en-PH", "fil-PH"],
        accept_languages=[
            "en-PH,en;q=0.9,fil;q=0.8",
            "en-PH,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Manila"],
        currency="PHP",
    ),

    # Vietnam (+84)
    "84": CountryProfile(
        country_code="84",
        country_name="Vietnam",
        iso_code="VN",
        locales=["vi-VN", "en-VN"],
        accept_languages=[
            "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "vi,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Ho_Chi_Minh"],
        currency="VND",
    ),

    # Malaysia (+60)
    "60": CountryProfile(
        country_code="60",
        country_name="Malaysia",
        iso_code="MY",
        locales=["ms-MY", "en-MY"],
        accept_languages=[
            "ms-MY,ms;q=0.9,en-US;q=0.8,en;q=0.7",
            "en-MY,en;q=0.9,ms;q=0.8",
        ],
        timezones=["Asia/Kuala_Lumpur"],
        currency="MYR",
    ),

    # South Africa (+27)
    "27": CountryProfile(
        country_code="27",
        country_name="South Africa",
        iso_code="ZA",
        locales=["en-ZA", "af-ZA"],
        accept_languages=[
            "en-ZA,en;q=0.9",
            "en-ZA,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Africa/Johannesburg"],
        currency="ZAR",
    ),

    # New Zealand (+64)
    "64": CountryProfile(
        country_code="64",
        country_name="New Zealand",
        iso_code="NZ",
        locales=["en-NZ"],
        accept_languages=[
            "en-NZ,en;q=0.9",
            "en-NZ,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Pacific/Auckland"],
        currency="NZD",
    ),

    # Argentina (+54)
    "54": CountryProfile(
        country_code="54",
        country_name="Argentina",
        iso_code="AR",
        locales=["es-AR", "en-AR"],
        accept_languages=[
            "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "es,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["America/Argentina/Buenos_Aires"],
        currency="ARS",
    ),

    # Colombia (+57)
    "57": CountryProfile(
        country_code="57",
        country_name="Colombia",
        iso_code="CO",
        locales=["es-CO", "en-CO"],
        accept_languages=[
            "es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "es,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["America/Bogota"],
        currency="COP",
    ),

    # Chile (+56)
    "56": CountryProfile(
        country_code="56",
        country_name="Chile",
        iso_code="CL",
        locales=["es-CL", "en-CL"],
        accept_languages=[
            "es-CL,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "es,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["America/Santiago"],
        currency="CLP",
    ),

    # Ireland (+353)
    "353": CountryProfile(
        country_code="353",
        country_name="Ireland",
        iso_code="IE",
        locales=["en-IE", "ga-IE"],
        accept_languages=[
            "en-IE,en;q=0.9",
            "en-IE,en-GB;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Dublin"],
        currency="EUR",
    ),

    # Belarus (+375)
    "375": CountryProfile(
        country_code="375",
        country_name="Belarus",
        iso_code="BY",
        locales=["be-BY", "ru-BY", "en-BY"],
        accept_languages=[
            "be-BY,be;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6",
            "ru-BY,ru;q=0.9,be;q=0.8,en-US;q=0.7,en;q=0.6",
            "ru,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Europe/Minsk"],
        currency="BYN",
    ),

    # Madagascar (+261)
    "261": CountryProfile(
        country_code="261",
        country_name="Madagascar",
        iso_code="MG",
        locales=["mg-MG", "fr-MG", "en-MG"],
        accept_languages=[
            "fr-MG,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "mg,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "fr,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Indian/Antananarivo"],
        currency="MGA",
    ),

    # Jordan (+962)
    "962": CountryProfile(
        country_code="962",
        country_name="Jordan",
        iso_code="JO",
        locales=["ar-JO", "en-JO"],
        accept_languages=[
            "ar-JO,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "ar,en-US;q=0.9,en;q=0.8",
            "en-JO,en;q=0.9,ar;q=0.8",
        ],
        timezones=["Asia/Amman"],
        currency="JOD",
    ),

    # Cambodia (+855)
    "855": CountryProfile(
        country_code="855",
        country_name="Cambodia",
        iso_code="KH",
        locales=["km-KH", "en-KH"],
        accept_languages=[
            "km-KH,km;q=0.9,en-US;q=0.8,en;q=0.7",
            "en-KH,en;q=0.9,km;q=0.8",
            "en,km;q=0.9",
        ],
        timezones=["Asia/Phnom_Penh"],
        currency="KHR",
    ),

    # Benin (+229)
    "229": CountryProfile(
        country_code="229",
        country_name="Benin",
        iso_code="BJ",
        locales=["fr-BJ", "en-BJ"],
        accept_languages=[
            "fr-BJ,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "fr,en-US;q=0.9,en;q=0.8",
            "en-BJ,en;q=0.9,fr;q=0.8",
        ],
        timezones=["Africa/Porto-Novo"],
        currency="XOF",
    ),

    # Georgia (+995)
    "995": CountryProfile(
        country_code="995",
        country_name="Georgia",
        iso_code="GE",
        locales=["ka-GE", "en-GE"],
        accept_languages=[
            "ka-GE,ka;q=0.9,en-US;q=0.8,en;q=0.7",
            "ka,en-US;q=0.9,en;q=0.8",
            "en-GE,en;q=0.9,ka;q=0.8",
        ],
        timezones=["Asia/Tbilisi"],
        currency="GEL",
    ),

    # Cuba (+53)
    "53": CountryProfile(
        country_code="53",
        country_name="Cuba",
        iso_code="CU",
        locales=["es-CU", "en-CU"],
        accept_languages=[
            "es-CU,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "es,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["America/Havana"],
        currency="CUP",
    ),

    # Nepal (+977)
    "977": CountryProfile(
        country_code="977",
        country_name="Nepal",
        iso_code="NP",
        locales=["ne-NP", "en-NP"],
        accept_languages=[
            "ne-NP,ne;q=0.9,en-US;q=0.8,en;q=0.7",
            "en-NP,en;q=0.9,ne;q=0.8",
        ],
        timezones=["Asia/Kathmandu"],
        currency="NPR",
    ),

    # Lebanon (+961)
    "961": CountryProfile(
        country_code="961",
        country_name="Lebanon",
        iso_code="LB",
        locales=["ar-LB", "fr-LB", "en-LB"],
        accept_languages=[
            "ar-LB,ar;q=0.9,fr;q=0.8,en-US;q=0.7,en;q=0.6",
            "fr-LB,fr;q=0.9,ar;q=0.8,en-US;q=0.7,en;q=0.6",
            "en-LB,en;q=0.9,ar;q=0.8,fr;q=0.7",
        ],
        timezones=["Asia/Beirut"],
        currency="LBP",
    ),

    # Uzbekistan (+998)
    "998": CountryProfile(
        country_code="998",
        country_name="Uzbekistan",
        iso_code="UZ",
        locales=["uz-UZ", "ru-UZ", "en-UZ"],
        accept_languages=[
            "uz-UZ,uz;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6",
            "ru-UZ,ru;q=0.9,uz;q=0.8,en-US;q=0.7,en;q=0.6",
            "ru,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Asia/Tashkent", "Asia/Samarkand"],
        currency="UZS",
    ),

    # Burkina Faso (+226)
    "226": CountryProfile(
        country_code="226",
        country_name="Burkina Faso",
        iso_code="BF",
        locales=["fr-BF", "en-BF"],
        accept_languages=[
            "fr-BF,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "fr,en-US;q=0.9,en;q=0.8",
        ],
        timezones=["Africa/Ouagadougou"],
        currency="XOF",
    ),
    "92": CountryProfile(
        country_code="92",
        country_name="Pakistan",
        iso_code="PK",
        locales=["en-PK", "ur-PK"],
        accept_languages=[
            "en-PK,en;q=0.9,ur;q=0.8",
        ],
        timezones=["Asia/Karachi"],
        currency="PKR",
    ),
}

# Default profile for unknown country codes (fallback to US)
DEFAULT_PROFILE = COUNTRY_PROFILES["1"]


class CountryProfileManager:
    """
    Manages country profiles for fingerprint matching.

    Provides methods to lookup profiles by phone number,
    country code, or ISO code.
    """

    def __init__(self):
        self.log = get_logger("CountryProfileManager")
        self._profiles = COUNTRY_PROFILES

    def get_by_country_code(self, country_code: str) -> CountryProfile:
        """
        Get a country profile by phone country code.

        Args:
            country_code: Phone country code (e.g., "380", "1", "44").

        Returns:
            CountryProfile for the country, or default if not found.
        """
        # Remove leading + or 0 if present
        country_code = country_code.lstrip("+").lstrip("0")

        profile = self._profiles.get(country_code)
        if profile:
            self.log.debug(f"Found profile for country code {country_code}: {profile.country_name}")
            return profile

        self.log.warning(f"No profile for country code {country_code}, using default (US)")
        return DEFAULT_PROFILE

    def get_by_phone_number(self, phone_number: str) -> CountryProfile:
        """
        Get a country profile by extracting country code from phone number.

        Args:
            phone_number: Full phone number (e.g., "+380969200145").

        Returns:
            CountryProfile for the phone's country.
        """
        # Clean the phone number
        phone = phone_number.strip().lstrip("+").lstrip("0")

        # Try to match country codes (longest first)
        # Sort codes by length descending to match 3-digit codes before 1-digit
        sorted_codes = sorted(self._profiles.keys(), key=len, reverse=True)

        for code in sorted_codes:
            if phone.startswith(code):
                return self.get_by_country_code(code)

        self.log.warning(f"Could not extract country code from {phone_number}, using default")
        return DEFAULT_PROFILE

    def get_by_iso_code(self, iso_code: str) -> Optional[CountryProfile]:
        """
        Get a country profile by ISO country code.

        Args:
            iso_code: ISO 3166-1 alpha-2 code (e.g., "UA", "US").

        Returns:
            CountryProfile or None if not found.
        """
        iso_code = iso_code.upper()
        for profile in self._profiles.values():
            if profile.iso_code == iso_code:
                return profile
        return None

    @property
    def supported_countries(self) -> List[str]:
        """Get list of supported country codes."""
        return list(self._profiles.keys())

    @property
    def supported_country_names(self) -> List[str]:
        """Get list of supported country names."""
        return [p.country_name for p in self._profiles.values()]


# Singleton instance
_profile_manager: Optional[CountryProfileManager] = None


def get_country_profile_manager() -> CountryProfileManager:
    """Get or create the country profile manager instance."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = CountryProfileManager()
    return _profile_manager


def get_profile_for_phone(phone_number: str) -> CountryProfile:
    """
    Convenience function to get a country profile for a phone number.

    Args:
        phone_number: Full phone number with country code.

    Returns:
        CountryProfile for the phone's country.
    """
    return get_country_profile_manager().get_by_phone_number(phone_number)
