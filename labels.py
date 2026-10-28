"""Cause and target group of an opportunity, read from its Arabic title.

Ehsan's completed archive has no cause filter, so completed projects are
labelled here. Two ordered rule lists; the first rule whose pattern matches
the title wins:

- CAUSE: *what* the opportunity provides, using Ehsan's own project types
  (Health, Education, Housing, Feeding, Religious, Environmental, Social).
  Concrete goods (food and water, a home) are checked before who-words such
  as patients or students: "meals for university students" is Feeding.
- TARGET_GROUP: *who* receives it.

Titles are normalised first (no diacritics or tatweel, one form of alef,
yaa and taa marbuta), so patterns are written in that normalised form.
"""
import re

import pandas as pd


def normalise(text):
    if not isinstance(text, str):
        return ""
    t = re.sub("[ً-ْـ‎‏]", "", text)
    t = re.sub("[أإآ]", "ا", t).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", " ", t).strip()


# Order matters: the first match wins.
CAUSE = [
    # Conventions taken from Ehsan's own labels on open projects: income
    # projects, appliances, training and transport count as Social;
    # lessons for expatriate communities count as Religious.
    # Hand check (26 Oct) added: transport for patients, funeral washing rooms
    # (renovated, but not a home) and sewing machines (an income tool).
    ("Social", r"عربات|الاسر المنتجه|مشاريع انتاجيه|قوارب|مكائن الخياطه|خياطه|"
               r"تيسير نقل|وسائل النقل|وسيله النقل|وسيله نقل|نقل المرضي|نقل الجنائز|مغاسل الاموات|"
               r"تاهيل الشباب|تاهيل المتعففين|تدريب|كهربائيه|اجهزه منزليه|رضع"),
    ("Religious", r"جاليات|دعاه|داعيه|دعوه"),
    ("Feeding", r"طعام|غذاء|وجبات|وجبه|افطار|سحور|سلال|سله|غذائي|تموين|لحوم|تمور|اضاحي|"
                r"سقيا|مياه|\bماء|الماء|برادات|زكاه الفطر|خبز|حليب"),
    ("Housing", r"ترميم|مساكن|مسكن|منازل|منزل|ايجار|تاثيث|سكن|فواتير|تدفئه|دفايات|بطانيات|مكيفات"),
    ("Health", r"مرض|مريض|مصاب|علاج|صحي|طبي|ادويه|دواء|غسيل|كلوي|الكلي\b|جراح|عمليه|عمليات|"
               r"سرطان|عيون|العين\b|قلب|اسنان|سكري|انسولين|ورم|اورام|شلل|ضمور|غضروف|مفصل|"
               r"قرنيه|قسطره|نطق|تخاطب|اعاقه|سمعيه|سمع|اذن|قوقعه|نظارات|اطراف|اكسجين|"
               r"كراسي متحركه|كرسي متحرك|اسعاف|توحد|متلازمه|تدخين|ادمان|مكفوف|بصر|اوكسجين|"
               r"طرف صناعي|قياس السكر|التبرع بالدم|ولاده|حوامل"),
    # "جامع" alone means a mosque, so only university forms count here
    ("Education", r"تعليم|طلاب|طالب|طالبات|مدرس|دراس|جامعه|جامعي|جامعات|حقيبه|دورات|منح|محو الاميه"),
    ("Religious", r"قران|تحفيظ|حفظه|مصاحف|مصحف|عمره|حج|ضيوف الرحمن|مساجد|مسجد|جامع\b|اعتكاف|شرعي"),
    ("Environmental", r"اشجار|تشجير|تصحر|بيئ|نظافه|تدوير|غرس|زراعه (ال)?(اشجار|نخيل)"),
    ("Social", r"كفاله|ارامل|مطلقات|ايتام|يتيم|زواج|سجناء|كرب|كسوه|اعانه|دعم|رعايه|موتي|"
               r"جنائز|اموات|مسنين|كبار السن|معسر|ديون|اسر|سداد|مستلزمات"),
]

TARGET_GROUP = [
    ("Orphans", r"يتيم|ايتام"),
    ("Widows & divorced women", r"ارامل|ارمله|مطلقات|مطلقه"),
    ("Prisoners' families", r"سجناء|سجين|نزلاء|مفرج عنهم"),
    ("Patients", r"مرض|مريض|مصاب|غسيل|كلوي|جراح|علاج|سرطان|طبي|ادويه|عمليه|عمليات|سكري|ورم|اورام"),
    ("People with disabilities", r"اعاقه|ذوي الهمم|مكفوف|صم\b|اطراف|كراسي متحركه"),
    ("Elderly", r"كبار السن|مسن"),
    ("Children", r"اطفال|طفل|رضع"),
    # Students means students from families in need. Quran circles and their
    # teachers are not need-based, so they fall through to General public.
    ("Students", r"طلاب|طالب|طالبات|جامعي|حقيبه مدرسيه|دارسين"),
    ("Couples marrying", r"زواج|متزوجين"),
    ("Pilgrims & worshippers", r"حجاج|حج\b|ضيوف الرحمن|معتمر|عمره|صائمين|صائم|افطار|حرم|"
                               r"مصلين|مساجد|مسجد|جاليات|دعاه"),
    ("Families in need", r"اسر|اسره|متعفف|محتاج|معسر|فقراء|مستحقين|ذوي الدخل|كرب"),
]


def classify(title, rules, default):
    t = normalise(title)
    for label, pattern in rules:
        if re.search(pattern, t):
            return label
    return default


def label_titles(titles):
    """DataFrame with cause and target_group for each title."""
    s = pd.Series(titles)
    return pd.DataFrame({
        "cause": s.map(lambda t: classify(t, CAUSE, "Other")),
        "target_group": s.map(lambda t: classify(t, TARGET_GROUP, "General public")),
    }, index=s.index)
