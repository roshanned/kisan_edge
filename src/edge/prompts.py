"""Prompts and safe-deferral answers shared by generation and fine-tuning."""
import re

SYSTEM_PROMPT = {
    "deva": "आप उत्तर प्रदेश के किसानों के लिए एक कृषि सलाहकार हैं। छोटा, सही और सरल हिंदी में उत्तर दें।",
    "hinglish": "आप उत्तर प्रदेश के किसानों के लिए एक कृषि सलाहकार हैं। सरल हिंदी में छोटा उत्तर दें।",
    "en": "You are an agricultural advisor for farmers in Uttar Pradesh, India. Answer briefly and correctly.",
}

# Offline answers for high-risk questions: general safety advice, never a number (proposal 7.3 A).
HIGH_RISK_ANSWER = {
    "deva": "दवा या खाद की सही मात्रा के लिए पैकेट पर लिखे निर्देश ध्यान से पढ़ें। छिड़काव के समय दस्ताने और मास्क पहनें। "
            "अपने नज़दीकी कृषि विज्ञान केंद्र (KVK) या किसान कॉल सेंटर 1800-180-1551 से सलाह लें। "
            "आपका सवाल सही मात्रा के साथ जवाब के लिए भेज दिया गया है।",
    "hinglish": "Dawa ya khad ki sahi matra ke liye packet par likhe nirdesh dhyan se padhein. Chhidkav ke samay dastane "
                "aur mask pahnein. Apne nazdeeki Krishi Vigyan Kendra (KVK) ya Kisan Call Centre 1800-180-1551 se salah "
                "lein. Aapka sawal sahi matra ke saath jawab ke liye bhej diya gaya hai.",
    "en": "For the correct dose, read the instructions on the product label carefully. Wear gloves and a mask while "
          "spraying. Ask your nearest Krishi Vigyan Kendra (KVK) or the Kisan Call Centre at 1800-180-1551. "
          "Your question has been queued for an answer with the exact dose.",
}

# Offline answers for live-data questions (weather, prices, schemes): defer, don't guess.
LIVE_DATA_ANSWER = {
    "deva": "यह जानकारी (जैसे मौसम, मंडी भाव या योजना) रोज़ बदलती है। इंटरनेट मिलते ही आपको ताज़ा जानकारी भेजी जाएगी।",
    "hinglish": "Yeh jankari (jaise mausam, mandi bhav ya yojana) roz badalti hai. Internet milte hi aapko taaza "
                "jankari bheji jayegi.",
    "en": "This information (such as weather, market prices or scheme rules) changes often. You will get the latest "
          "details as soon as you are back online.",
}

# Any digit (Latin or Devanagari) next to a dose unit counts as a dose.
DOSE = re.compile(r"[\d०-९]+\s*(%|ml|मि\.?\s?ली|ग्राम|gram|gm|g\b|kg|किलो|कि\.?\s?ग्रा|किग्रा|ग्रा|kilo|"
                  r"litre|liter|लीटर|ली\b|ltr|/)", re.I)


def prompt_kind(row):
    if row["script"] == "deva":
        return "deva"
    return "hinglish" if row["lang"] == "hi" else "en"


def has_dose(text):
    return bool(DOSE.search(text))


def messages(row, answer=None):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT[prompt_kind(row)]},
            {"role": "user", "content": row["question"]}]
    if answer is not None:
        msgs.append({"role": "assistant", "content": answer})
    return msgs
