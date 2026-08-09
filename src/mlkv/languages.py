"""Language metadata for the experiment matrix.

Instruction strings are deliberately short and FROZEN (prompt_version below):
they are a controlled constant across compression configs, so any translation
imperfection cancels out in within-language compression deltas.
"""

from __future__ import annotations

from dataclasses import dataclass

# Bump only with a conscious decision — invalidates result-store keys.
PROMPT_VERSION = "v1"


@dataclass(frozen=True)
class Language:
    code: str            # ISO 639-1 as used by MGSM/our loaders
    name: str
    script: str          # dominant Unicode script name
    in_mgsm: bool        # natively in juletxara/mgsm
    glotlid: str         # GlotLID label (ISO 639-3 + script)
    instruction: str     # native one-line CoT instruction with '####' marker
    qa_instruction: str  # native one-line RAG-QA instruction with '####' marker


LANGUAGES: dict[str, Language] = {
    lang.code: lang
    for lang in [
        Language("en", "English", "Latin", True, "eng_Latn",
                 "Solve the problem step by step. End your reply with '#### <final numeric answer>'.",
                 "Answer the question using only the passages above. End your reply with '#### <exact answer span>'."),
        Language("es", "Spanish", "Latin", True, "spa_Latn",
                 "Resuelve el problema paso a paso. Termina tu respuesta con '#### <respuesta numérica final>'.",
                 "Responde a la pregunta usando solo los pasajes anteriores. Termina tu respuesta con '#### <fragmento exacto de la respuesta>'."),
        Language("fr", "French", "Latin", True, "fra_Latn",
                 "Résous le problème étape par étape. Termine ta réponse par '#### <réponse numérique finale>'.",
                 "Réponds à la question en utilisant uniquement les passages ci-dessus. Termine ta réponse par '#### <extrait exact de la réponse>'."),
        Language("de", "German", "Latin", True, "deu_Latn",
                 "Löse die Aufgabe Schritt für Schritt. Beende deine Antwort mit '#### <endgültige Zahl>'.",
                 "Beantworte die Frage nur anhand der obigen Abschnitte. Beende deine Antwort mit '#### <exakte Antwortpassage>'."),
        Language("ru", "Russian", "Cyrillic", True, "rus_Cyrl",
                 "Реши задачу шаг за шагом. Заверши ответ строкой '#### <итоговое число>'.",
                 "Ответь на вопрос, используя только приведённые выше отрывки. Заверши ответ строкой '#### <точный фрагмент ответа>'."),
        Language("zh", "Chinese", "Han", True, "cmn_Hani",
                 "请逐步解答该问题。回答的最后一行写 '#### <最终数字答案>'。",
                 "请仅根据上文的段落回答问题。回答的最后一行写 '#### <原文中的答案片段>'。"),
        Language("ja", "Japanese", "Han", True, "jpn_Jpan",
                 "問題を段階的に解いてください。回答の最後に '#### <最終的な数値>' と書いてください。",
                 "上記の文章のみに基づいて質問に答えてください。回答の最後に '#### <本文中の正確な答え>' と書いてください。"),
        Language("th", "Thai", "Thai", True, "tha_Thai",
                 "จงแก้โจทย์ทีละขั้นตอน และจบคำตอบด้วย '#### <คำตอบตัวเลขสุดท้าย>'",
                 "จงตอบคำถามโดยใช้เฉพาะข้อความข้างต้นเท่านั้น และจบคำตอบด้วย '#### <ข้อความคำตอบตรงตามต้นฉบับ>'"),
        Language("sw", "Swahili", "Latin", True, "swh_Latn",
                 "Tatua tatizo hatua kwa hatua. Malizia jibu lako kwa '#### <jibu la mwisho la nambari>'.",
                 "Jibu swali ukitumia vifungu vilivyo hapo juu tu. Malizia jibu lako kwa '#### <kifungu halisi cha jibu>'."),
        Language("bn", "Bengali", "Bengali", True, "ben_Beng",
                 "ধাপে ধাপে সমস্যাটি সমাধান করো। উত্তরের শেষে লেখো '#### <চূড়ান্ত সংখ্যা>'।",
                 "শুধুমাত্র উপরের অনুচ্ছেদগুলি ব্যবহার করে প্রশ্নের উত্তর দাও। উত্তরের শেষে লেখো '#### <সঠিক উত্তরাংশ>'।"),
        Language("te", "Telugu", "Telugu", True, "tel_Telu",
                 "సమస్యను దశలవారీగా పరిష్కరించండి. మీ సమాధానం చివర '#### <తుది సంఖ్య>' రాయండి.",
                 "పై పేరాగ్రాఫ్‌లను మాత్రమే ఉపయోగించి ప్రశ్నకు సమాధానం ఇవ్వండి. సమాధానం చివర '#### <ఖచ్చితమైన సమాధాన భాగం>' రాయండి."),
        Language("vi", "Vietnamese", "Latin", False, "vie_Latn",
                 "Hãy giải bài toán từng bước. Kết thúc câu trả lời bằng '#### <đáp số>'.",
                 "Chỉ dựa vào các đoạn văn ở trên để trả lời câu hỏi. Kết thúc câu trả lời bằng '#### <cụm từ trả lời chính xác>'."),
    ]
}

# Characters unique to Vietnamese orthography among Latin-script languages here
# (used by the script-only drift fallback to separate VI from EN/SW/ES/FR/DE).
VIETNAMESE_MARKS = set(
    "ăâđêôơưĂÂĐÊÔƠƯ"
    "áàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠẮẰẲẴẶẤẦẨẪẬÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ"
)


def resolve(codes: str | list[str]) -> list[Language]:
    """Resolve 'en,vi' / 'all' / list into Language objects."""
    if isinstance(codes, str):
        if codes == "all":
            return list(LANGUAGES.values())
        codes = [c.strip() for c in codes.split(",") if c.strip()]
    return [LANGUAGES[c] for c in codes]
