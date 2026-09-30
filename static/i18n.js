/* Arabic interface layer. Translates UI text nodes, titles and placeholders after every render
   via a MutationObserver, so app.js stays language-agnostic. Engagement data stays as entered. */
(function () {
  const D = {
    // shell
    "Benchmark Studio": "استوديو المقارنة المعيارية", "Mushar Consulting": "مُشار للاستشارات",
    "Engagements": "المشاريع", "Review queue": "طابور المراجعة", "Governance": "الحوكمة", "Source rules": "قواعد المصادر",
    "Prompt library": "مكتبة التعليمات", "Quality insights": "مؤشرات الجودة", "Audit log": "سجل التدقيق", "Settings": "الإعدادات",
    "AI accelerates.": "الذكاء الاصطناعي يسرّع.", "Evidence governs.": "الأدلة تحكم.", "Consultants decide.": "المستشارون يقررون.",
    "Acting as": "تعمل بصفة", "● Demo AI mode": "● وضع الذكاء الاصطناعي التجريبي", "العربية": "English",
    "Read-only preview with demo data. Browse every stage, open research cells and evidence, and switch roles. Editing, AI runs and exports need the running platform.":
      "نسخة استعراض للقراءة فقط ببيانات تجريبية. تصفّح كل المراحل، وافتح خلايا البحث والأدلة، وبدّل الأدوار. التعديل وتشغيل الذكاء الاصطناعي والتصدير تحتاج المنصة المشغّلة.",
    "Read-only preview. Changes are available in the running platform.": "نسخة للقراءة فقط. التعديل متاح في المنصة المشغّلة.",
    "Not included in this preview.": "غير متضمن في هذه النسخة.",
    // roles
    "Admin": "مدير النظام", "Engagement Lead": "قائد المشروع", "Consultant": "مستشار", "Reviewer": "مراجع", "Qa Lead": "مسؤول الجودة", "Viewer": "مشاهد",
    "Platform Admin": "مدير المنصة", "Guest Viewer": "زائر (مشاهدة)",
    // home
    "Benchmarking engagements": "مشاريع المقارنة المعيارية",
    "Each engagement moves through seven gated stages. AI drafts at every step; nothing reaches a client deliverable without human approval.":
      "كل مشروع يمر بسبع مراحل ببوابات اعتماد. الذكاء الاصطناعي يكتب المسودات في كل خطوة، ولا يصل شيء إلى مخرج العميل بدون اعتماد بشري.",
    "+ New engagement": "+ مشروع جديد", "Accepted evidence items": "أدلة مقبولة", "Items awaiting review": "عناصر بانتظار المراجعة",
    "Released deliverables": "مخرجات مُطلقة", "Released": "مُطلق", "No engagements yet.": "لا توجد مشاريع بعد.",
    "New benchmarking engagement": "مشروع مقارنة معيارية جديد", "Starts at Stage 0 — Brief & Scope.": "يبدأ من المرحلة 0: الموجز والنطاق.",
    "Title": "العنوان", "Client": "العميل", "Sector": "القطاع", "Objective": "الهدف", "Create engagement": "إنشاء المشروع", "Cancel": "إلغاء",
    "⬇ Evidence workbook": "⬇ ملف الأدلة (Excel)", "⬇ Deliverable (PPTX)": "⬇ المخرج (PPTX)", "⬇ Download PPTX": "⬇ تنزيل PPTX",
    // stages & gates
    "Brief & Scope": "الموجز والنطاق", "Framework": "الإطار", "Research": "البحث", "Benchmark": "المقارنة", "Synthesis": "التحليل والرؤى",
    "Deliverable": "المخرج", "QA & Release": "الجودة والإطلاق",
    "Scope Approved": "اعتماد النطاق", "Framework Approved": "اعتماد الإطار", "Evidence Reviewed": "مراجعة الأدلة", "Analysis Approved": "اعتماد التحليل",
    "Insight & Recommendation Approved": "اعتماد الرؤى والتوصيات", "Draft Approved": "اعتماد المسودة", "Final Approved": "الاعتماد النهائي",
    "Locked": "مقفل", "In progress": "قيد العمل", "Awaiting approval": "بانتظار الاعتماد", "Approved": "معتمد", "Returned": "مُعاد",
    "✓ Approve gate": "✓ اعتماد البوابة", "✓ Co-sign release": "✓ توقيع الإطلاق", "↩ Return": "↩ إعادة", "Reopen stage": "إعادة فتح المرحلة",
    "✓ All gate preconditions met": "✓ كل شروط البوابة مستوفاة", "Awaiting QA Lead co-sign.": "بانتظار توقيع مسؤول الجودة.",
    "Owner: Engagement Lead": "المسؤول: قائد المشروع", "Owner: Reviewer / Engagement Lead": "المسؤول: المراجع / قائد المشروع",
    "Owner: QA Lead co-sign + Engagement Lead": "المسؤول: توقيع مسؤول الجودة + قائد المشروع",
    "Submitted for approval": "أُرسل للاعتماد", "Gate decision recorded": "سُجّل قرار البوابة", "Returned for rework": "أُعيد للتعديل", "Stage reopened": "أُعيد فتح المرحلة",
    "Objective is required.": "الهدف مطلوب.", "Decision statement is required.": "بيان القرار مطلوب.", "Scope inclusions are required.": "ما يشمله النطاق مطلوب.",
    "The framework has no criteria.": "الإطار بلا معايير.", "All criteria must be approved.": "يجب اعتماد كل المعايير.",
    "Every criterion needs a structured question.": "كل معيار يحتاج سؤالًا مهيكلًا.", "At least 2 approved comparators are required.": "يلزم نموذجان مقارنان معتمدان على الأقل.",
    "Decide on all proposed comparators (approve or reject).": "قرر في كل النماذج المقترحة (اعتماد أو رفض).", "No research tasks.": "لا توجد مهام بحث.",
    "No approved content in this stage.": "لا يوجد محتوى معتمد في هذه المرحلة.", "Generate and review the storyline first.": "أنشئ الخط السردي وراجعه أولًا.",
    // brief
    "Introduction & brief": "المقدمة والموجز", "AI helps articulate the assignment; the engagement lead owns intent.": "الذكاء الاصطناعي يساعد في صياغة المهمة، وقائد المشروع يملك القصد.",
    "Objective *": "الهدف *", "Engagement context": "سياق المشروع", "Decision the study supports *": "القرار الذي تدعمه الدراسة *", "Expected outcomes": "النتائج المتوقعة",
    "Scope": "النطاق", "No research starts before scope is clear. Factual assumptions must be flagged, not invented.": "لا يبدأ البحث قبل وضوح النطاق. الافتراضات يجب أن تُعلَّم لا أن تُخترع.",
    "Inclusions *": "ما يشمله *", "Exclusions": "ما يستثنيه", "Geography": "النطاق الجغرافي", "Named entities / comparators (optional, comma-separated)": "الجهات المقارنة (اختياري، مفصولة بفواصل)",
    "Period": "الفترة", "Constraints": "القيود", "Save brief & scope": "حفظ الموجز والنطاق", "Brief saved": "تم حفظ الموجز",
    // framework
    "Benchmark framework": "إطار المقارنة المعيارية", "AI proposes a bespoke framework; the consultant decides. Edits are captured as feedback for prompt improvement.":
      "الذكاء الاصطناعي يقترح إطارًا مخصصًا، والمستشار يقرر. التعديلات تُحفظ كملاحظات لتحسين التعليمات.",
    "Generate framework with AI": "توليد الإطار بالذكاء الاصطناعي", "Regenerate framework with AI": "إعادة توليد الإطار بالذكاء الاصطناعي",
    "Approve all criteria": "اعتماد كل المعايير", "+ Dimension": "+ محور", "+ Criterion": "+ معيار", "+ Comparator": "+ نموذج مقارن", "Weight": "الوزن",
    "Structured research question": "سؤال البحث المهيكل", "Indicator": "المؤشر", "unit": "الوحدة",
    "Relevance · Researchability · Comparability": "الأهمية · قابلية البحث · قابلية المقارنة", "High": "عالية", "Medium": "متوسطة", "Low": "منخفضة",
    "rating": "تقييم", "checklist": "قائمة تحقق", "quantitative": "كمي", "qualitative": "نوعي", "higher_better": "الأعلى أفضل", "lower_better": "الأقل أفضل",
    "Proposed": "مقترح", "Unapprove": "إلغاء الاعتماد", "Approve": "اعتماد", "Reject": "رفض", "No criteria.": "لا توجد معايير.",
    "No framework yet. Generate one with AI or add dimensions manually.": "لا يوجد إطار بعد. ولّده بالذكاء الاصطناعي أو أضف المحاور يدويًا.",
    "Comparator set": "مجموعة النماذج المقارنة", "Comparator": "النموذج المقارن", "Type": "النوع", "Region": "المنطقة", "Selection rationale": "مبرر الاختيار", "Status": "الحالة",
    "organization": "جهة", "country": "دولة", "practice": "ممارسة", "Saved": "تم الحفظ",
    "Replace the current framework with a new AI proposal?": "استبدال الإطار الحالي بمقترح جديد من الذكاء الاصطناعي؟",
    "Delete this criterion?": "حذف هذا المعيار؟", "Delete this dimension and its criteria?": "حذف هذا المحور ومعاييره؟",
    // research
    "Research matrix": "مصفوفة البحث", "Evidence repository": "مستودع الأدلة", "Evidence base: comparator × question": "قاعدة الأدلة: نموذج مقارن × سؤال",
    "Primary-source-first. No material statement without traceable evidence. “Unknown” when evidence is insufficient.":
      "المصدر الأولي أولًا. لا عبارة جوهرية بلا دليل يمكن تتبعه. «غير معروف» عندما تكون الأدلة غير كافية.",
    "Tasks closed": "مهام مغلقة", "AI drafts awaiting review": "مسودات بانتظار المراجعة", "Evidence items pending": "أدلة معلّقة", "Evidence gaps (disclosed)": "فجوات أدلة (مُفصح عنها)",
    "Not started": "لم يبدأ", "Draft – review": "مسودة للمراجعة", "Complete": "مكتمل", "Evidence gap": "فجوة أدلة", "Researching…": "جارٍ البحث…", "In review": "قيد المراجعة",
    "Criterion / question": "المعيار / السؤال", "Unknown": "غير معروف", "Assessed": "تم التقييم", "Insufficient evidence": "أدلة غير كافية",
    "sufficient": "كافية", "partial": "جزئية", "gap": "فجوة", "conflict": "تعارض", "yes": "نعم", "no": "لا", "unknown": "غير معروف",
    "Close ✕": "إغلاق ✕", "Draft response": "المسودة", "PENDING HUMAN REVIEW": "بانتظار المراجعة البشرية", "Assessment": "التقييم", "Sufficiency": "كفاية الأدلة",
    "0 — Absent (authoritative evidence)": "0 — غائب (بدليل موثوق)", "1 — Initial": "1 — أولي", "2 — Developing": "2 — نامٍ", "3 — Established": "3 — راسخ", "4 — Leading": "4 — رائد",
    "Comparability checks (all four required before scoring)": "فحوصات قابلية المقارنة (الأربعة مطلوبة قبل التقييم)",
    "definition": "التعريف", "period": "الفترة", "denominator": "المقام", "Qualitative — response text only": "نوعي: نص الإجابة فقط",
    "Save": "حفظ", "✓ Mark complete": "✓ إكمال المهمة", "Close as evidence gap": "إغلاق كفجوة أدلة", "Re-run AI research": "إعادة البحث بالذكاء الاصطناعي",
    "+ Add evidence manually": "+ إضافة دليل يدويًا", "Add evidence": "إضافة دليل", "No evidence yet.": "لا توجد أدلة بعد.",
    "Accepted": "مقبول", "Rejected": "مرفوض", "Pending review": "بانتظار المراجعة", "More research": "بحث إضافي", "Disclosed gap": "فجوة مُفصح عنها",
    "Accept": "قبول", "Request more research": "طلب بحث إضافي", "Log": "تسجيل", "Log a manual search query": "سجّل عملية بحث يدوية",
    "At least 3 logged searches are required before closing a task as a gap.": "يلزم تسجيل 3 عمليات بحث على الأقل قبل إغلاق المهمة كفجوة.",
    "Task completed": "اكتملت المهمة", "Closed as evidence gap": "أُغلقت كفجوة أدلة", "Priority updated": "تم تحديث الأولوية",
    "Reason for rejecting this source:": "سبب رفض هذا المصدر:", "What additional research is needed?": "ما البحث الإضافي المطلوب؟",
    "claim": "الادعاء", "publisher": "الناشر", "title": "العنوان", "pub date": "تاريخ النشر", "url": "الرابط", "locator": "الصفحة/القسم",
    "Priority": "الأولوية", "Source category": "فئة المصدر", "Verbatim excerpt (snapshot)": "مقتطف حرفي (نسخة محفوظة)",
    "All statuses": "كل الحالات", "ID": "المعرّف", "Comparator · criterion": "النموذج · المعيار", "Claim": "الادعاء", "Source": "المصدر",
    "pending": "معلّق", "accepted": "مقبول", "rejected": "مرفوض", "more_research": "بحث إضافي",
    // benchmark
    "Compare & assess": "المقارنة والتقييم", "AI drafts only from reviewed evidence. Comparisons are computed from the matrix — never free-written. Unknown ≠ 0.":
      "الذكاء الاصطناعي يكتب من الأدلة المراجَعة فقط. المقارنات تُحسب من المصفوفة ولا تُكتب بحرّية. غير معروف ≠ صفر.",
    "Draft profiles & comparisons with AI": "صياغة الملفات والمقارنات بالذكاء الاصطناعي", "Scored comparison matrix": "مصفوفة المقارنة المرجّحة",
    "Dimension / criterion": "المحور / المعيار", "Type · wt": "النوع · الوزن", "Overall score": "النتيجة الكلية", "coverage": "التغطية",
    "Cross-comparator comparisons": "مقارنات بين النماذج", "No benchmark content yet.": "لا يوجد محتوى مقارنة بعد.",
    "Verified fact": "حقيقة موثقة", "Benchmark comparison": "مقارنة معيارية", "AI synthesis": "تركيب (ذكاء اصطناعي)", "AI interpretation": "تفسير (ذكاء اصطناعي)",
    "Client implication": "دلالة للعميل", "Research gap": "فجوة بحثية", "Human-written": "كتابة بشرية", "AI draft": "مسودة ذكاء اصطناعي",
    "Evidence:": "الأدلة:", "none linked": "لا يوجد ربط", "Edit": "تعديل", "Approve as limitation": "اعتماد كقيد", "Assumptions / conditions: ": "الافتراضات / الشروط: ",
    "Edit content item": "تعديل عنصر المحتوى", "Content type": "نوع المحتوى", "Text": "النص", "Reason for change (optional)": "سبب التعديل (اختياري)",
    "Linked evidence (accepted only)": "الأدلة المرتبطة (المقبولة فقط)", "AI original": "النص الأصلي من الذكاء الاصطناعي",
    "Edits are stored as feedback (AI original vs. approved wording) and send the item back to review.": "التعديلات تُحفظ كملاحظات (النص الأصلي مقابل المعتمد) وتُعيد العنصر للمراجعة.",
    "Saved — back in review": "تم الحفظ، وعاد للمراجعة",
    // synthesis
    "Insights, lessons & recommendations": "الرؤى والدروس والتوصيات",
    "AI synthesis and interpretation are labelled and kept separate from sourced facts. Human judgement is mandatory for client recommendations.":
      "التركيب والتفسير من الذكاء الاصطناعي معلّمان ومنفصلان عن الحقائق الموثقة. الحكم البشري إلزامي في توصيات العميل.",
    "Synthesise with AI": "التحليل بالذكاء الاصطناعي", "+ Add recommendation": "+ إضافة توصية", "Lessons learned": "الدروس المستفادة",
    "Client implications & recommendation options": "دلالات للعميل وخيارات التوصيات", "Limitations & research gaps": "القيود والفجوات البحثية", "None yet.": "لا شيء بعد.",
    "Recommendation text:": "نص التوصية:",
    // deliverable
    "Build the deliverable": "بناء المخرج", "Storyline built only from approved content. No new facts are introduced to strengthen the story.":
      "الخط السردي يُبنى من المحتوى المعتمد فقط، ولا تُضاف حقائق جديدة لتقوية القصة.",
    "Build storyline with AI": "بناء الخط السردي بالذكاء الاصطناعي", "Rebuild storyline with AI": "إعادة بناء الخط السردي بالذكاء الاصطناعي",
    "Executive summary": "الملخص التنفيذي", "Build the storyline to draft the executive summary.": "ابنِ الخط السردي لصياغة الملخص التنفيذي.",
    "Slide outline": "مخطط الشرائح", "unapproved item": "عنصر غير معتمد", "No storyline yet.": "لا يوجد خط سردي بعد.", "References": "المراجع",
    "(generated automatically from accepted evidence cited in approved content)": "(تُولَّد تلقائيًا من الأدلة المقبولة المستشهد بها في المحتوى المعتمد)",
    "No cited references yet.": "لا توجد مراجع بعد.",
    // QA
    "Validate & approve": "التحقق والاعتماد", "Critical issues block release. Final release requires Engagement Lead approval and QA Lead co-sign.":
      "المشكلات الحرجة تمنع الإطلاق. الإطلاق النهائي يتطلب اعتماد قائد المشروع وتوقيع مسؤول الجودة.",
    "↻ Re-run rule checks": "↻ إعادة فحص القواعد", "Independent AI review": "مراجعة مستقلة بالذكاء الاصطناعي", "Critical (blocking)": "حرجة (مانعة)",
    "Major": "رئيسية", "Minor": "ثانوية", "Blocked": "ممنوع", "Clear": "جاهز", "Release status": "حالة الإطلاق", "Open issues": "المشكلات المفتوحة",
    "Rule": "القاعدة", "Severity": "الخطورة", "Issue": "المشكلة", "AI reviewer": "مراجع ذكاء اصطناعي", "Rule engine": "محرك القواعد", "Resolve": "حل", "go to →": "انتقال ←",
    "No open issues 🎉": "لا توجد مشكلات مفتوحة 🎉", "QA rule set": "قواعد الجودة", "Check": "الفحص", "critical": "حرجة", "major": "رئيسية", "minor": "ثانوية",
    "Fact or comparison with no linked evidence": "حقيقة أو مقارنة بلا دليل مرتبط", "Linked evidence is not accepted": "الدليل المرتبط غير مقبول",
    "Linked to a REJECT-category source": "مرتبط بمصدر من فئة مرفوضة", "Deliverable contains content that is not approved": "المخرج يحتوي محتوى غير معتمد",
    "Recommendation not reviewed by a human": "توصية لم يراجعها إنسان", "Quantitative value used without passed comparability checks": "قيمة كمية بدون اجتياز فحوصات قابلية المقارنة",
    "Accepted evidence missing publisher, title, date or URL": "دليل مقبول ينقصه الناشر أو العنوان أو التاريخ أو الرابط",
    "Framework question not researched (no completed or gap-closed task)": "سؤال في الإطار لم يُبحث (لا مهمة مكتملة أو مغلقة كفجوة)",
    "Synthesis/interpretation placed in a fact-only section": "تركيب/تفسير في قسم مخصص للحقائق فقط",
    "Research gaps exist but no limitation is disclosed": "توجد فجوات بحثية بدون إفصاح عنها كقيد", "Evidence older than 5 years (check it is the latest release)": "دليل أقدم من 5 سنوات (تأكد أنه أحدث إصدار)",
    "QA re-run": "أُعيد فحص الجودة",
    // queue / rules / prompts / insights / audit / settings
    "Everything the AI produced that still needs a human decision, across all engagements.": "كل ما أنتجه الذكاء الاصطناعي وما زال يحتاج قرارًا بشريًا، في كل المشاريع.",
    "Engagement": "المشروع", "Stage": "المرحلة", "Open →": "فتح ←", "Item": "العنصر", "None": "لا شيء",
    "Source hierarchy & credibility rules": "تسلسل المصادر وقواعد المصداقية",
    "Central policy injected into the research and source-validation agents. Edits apply to the next AI run.": "سياسة مركزية تُضخ في وكلاء البحث والتحقق من المصادر. التعديلات تسري من التشغيل التالي.",
    "Central policy injected into the research and source-validation agents. Only admins can edit.": "سياسة مركزية تُضخ في وكلاء البحث والتحقق من المصادر. التعديل لمدير النظام فقط.",
    "Category": "الفئة", "Examples": "أمثلة", "Preferred for": "مفضّل لـ", "Treatment": "المعاملة", "Key rule": "القاعدة الأساسية", "Additional evidence rules": "قواعد أدلة إضافية",
    "Policy updated": "تم تحديث السياسة",
    "The prompt/policy layer that “trains” the AI in the firm's method — explicit, versioned and editable without retraining. Placeholders like {{OBJECTIVE}} are filled at run time.":
      "طبقة التعليمات والسياسات التي «تدرّب» الذكاء الاصطناعي على منهجية الشركة: صريحة ومُصدَّرة وقابلة للتعديل بدون إعادة تدريب. العناصر مثل {{OBJECTIVE}} تُملأ عند التشغيل.",
    "Save new version": "حفظ نسخة جديدة", "Prompt saved as new version": "حُفظت التعليمات كنسخة جديدة",
    "Quality insights & feedback capture": "مؤشرات الجودة وتسجيل الملاحظات",
    "Expert corrections are stored as data for prompt improvement and future evaluation sets.": "تصحيحات الخبراء تُحفظ كبيانات لتحسين التعليمات ومجموعات التقييم المستقبلية.",
    "Evidence acceptance rate": "نسبة قبول الأدلة", "AI drafts edited by consultants": "مسودات عدّلها المستشارون", "Research gap rate": "نسبة الفجوات البحثية",
    "Evidence items collected": "أدلة مجموعة", "Evidence by source priority": "الأدلة حسب أولوية المصدر", "Rejected sources by category": "المصادر المرفوضة حسب الفئة",
    "Feedback captured": "الملاحظات المسجلة", "Feedback log": "سجل الملاحظات", "When": "الوقت", "Kind": "النوع", "Before": "قبل", "After / reason": "بعد / السبب", "By": "بواسطة", "No data": "لا بيانات",
    "edited_text": "نص معدّل", "framework_edit": "تعديل إطار", "rejected_source": "مصدر مرفوض", "qa_issue": "مشكلة جودة",
    "Every AI run, review decision, gate action and policy change.": "كل تشغيل للذكاء الاصطناعي وقرار مراجعة وإجراء بوابة وتغيير سياسة.",
    "When (UTC)": "الوقت (UTC)", "User": "المستخدم", "Action": "الإجراء", "Detail": "التفاصيل",
    "AI connection and roles.": "اتصال الذكاء الاصطناعي والأدوار.", "AI engine": "محرك الذكاء الاصطناعي", "Anthropic SDK installed": "حزمة Anthropic مثبتة",
    "API key (ANTHROPIC_API_KEY)": "مفتاح API", "Current mode": "الوضع الحالي", "Yes": "نعم", "No": "لا", "Detected": "موجود", "Not set": "غير مضبوط",
    "Live — Claude": "مباشر: Claude", "Demo generators": "مولّدات تجريبية", "Mode": "الوضع", "Auto (live when a key is present)": "تلقائي (مباشر عند وجود مفتاح)", "Demo only": "تجريبي فقط",
    "Model": "النموذج", "Switch to the Platform Admin user to change settings.": "بدّل إلى مدير المنصة لتغيير الإعدادات.",
    "Roles & permissions": "الأدوار والصلاحيات", "Capability": "الصلاحية", "Create engagement": "إنشاء مشروع", "Edit brief / framework / content": "تعديل الموجز / الإطار / المحتوى",
    "Run AI": "تشغيل الذكاء الاصطناعي", "Accept / reject evidence": "قبول / رفض الأدلة", "Approve content": "اعتماد المحتوى", "Submit gates": "إرسال البوابات", "QA": "الجودة",
    "Policies & settings": "السياسات والإعدادات", "Approve gates": "اعتماد البوابات", "✔ all": "✔ الكل", "Stage 2": "المرحلة 2", "Stage 6 co-sign": "توقيع المرحلة 6",
    "Settings saved": "تم حفظ الإعدادات", "Done": "تم",
    // v1.1 — requirements-driven workflow
    "⬇ Slides (PPTX)": "⬇ الشرائح (PPTX)", "⬇ Report (Word)": "⬇ التقرير (Word)", "← Back": "→ السابق", "Next →": "التالي ←", "Finish ✓": "إنهاء ✓",
    "Approve gate": "اعتماد البوابة", "Co-sign release": "توقيع الإطلاق",
    "Define the assignment in your own terms. Nothing here is tied to a predefined framework — the AI proposes the framework from what you write.":
      "عرّف المهمة بلغتك. لا شيء هنا مقيّد بإطار جاهز؛ الذكاء الاصطناعي يقترح الإطار مما تكتبه.",
    "Client requirements": "متطلبات العميل", "These drive the framework, the benchmark selection and the analysis method.": "هذه تحدد الإطار واختيار النماذج المقارنة ومنهج التحليل.",
    "Key questions the client wants answered * (one per line)": "الأسئلة الرئيسية التي يريد العميل إجابتها * (سؤال في كل سطر)",
    "What needs to be compared (one area per line)": "ما الذي يجب مقارنته (مجال في كل سطر)", "Other requirements": "متطلبات أخرى",
    "Benchmarks you already want included (optional, comma-separated)": "نماذج مقارنة تريد تضمينها (اختياري، مفصولة بفواصل)",
    "Analysis method": "منهج التحليل", "Qualitative": "نوعي", "Quantitative": "كمي", "Mixed": "مختلط",
    "descriptive comparison, practices and themes; no numeric scoring": "مقارنة وصفية وممارسات ومحاور، بدون درجات رقمية",
    "indicators and scores across comparable data": "مؤشرات ودرجات على بيانات قابلة للمقارنة",
    "qualitative assessment supported by selected indicators and scores": "تقييم نوعي مدعوم بمؤشرات ودرجات مختارة",
    "Select a method or let the AI recommend one.": "اختر منهجًا أو دع الذكاء الاصطناعي يوصي به.",
    "No key questions yet — add them in the brief so the AI can tailor the framework.": "لا توجد أسئلة رئيسية بعد؛ أضفها في الموجز ليصمم الذكاء الاصطناعي الإطار عليها.",
    "Compare:": "المقارنة:", "Built for this engagement from the requirements above. Add, edit or remove anything; edits are captured as feedback.":
      "مصمم لهذا المشروع من المتطلبات أعلاه. أضف أو عدّل أو احذف ما تشاء؛ التعديلات تُحفظ كملاحظات.",
    "Generate framework from requirements": "توليد الإطار من المتطلبات", "Regenerate framework from requirements": "إعادة توليد الإطار من المتطلبات",
    "Start blank": "البدء من الصفر", "Include in scoring": "ضمن الدرجات", "Benchmark selection": "اختيار النماذج المقارنة",
    "Countries, governments, organisations, companies, jurisdictions, operating models, programs or practices.": "دول أو حكومات أو جهات أو شركات أو ولايات قضائية أو نماذج تشغيل أو برامج أو ممارسات.",
    "+ Benchmark": "+ نموذج مقارن", "Benchmark": "النموذج المقارن", "Benchmark role": "دور النموذج", "— choose —": "— اختر —", "Benchmark roles explained": "شرح أدوار النماذج المقارنة",
    "Direct Comparator": "مقارن مباشر", "Highly comparable to the client": "مشابه جدًا للعميل", "Contextual Comparator": "مقارن سياقي", "Useful for contextual comparison": "مفيد للمقارنة السياقية",
    "Aspirational Benchmark": "نموذج طموح", "Relevant model the client may aspire toward": "نموذج قد يطمح العميل للوصول إليه", "Leading Practice": "ممارسة رائدة",
    "Demonstrates a specific practice": "يُظهر ممارسة محددة", "Country/Jurisdiction Benchmark": "مقارنة دولة / ولاية قضائية", "Provides country or regulatory comparison": "يوفر مقارنة على مستوى الدولة أو التنظيم",
    "Cross-Industry Benchmark": "مقارنة من قطاع آخر", "Transfers a relevant practice from another sector": "ينقل ممارسة مفيدة من قطاع آخر",
    "Practice/Model Benchmark": "مقارنة ممارسة / نموذج", "Focuses on a particular operating or service model": "يركز على نموذج تشغيل أو خدمة محدد",
    "Country": "دولة", "Government": "حكومة", "Organization": "جهة", "Company": "شركة", "Jurisdiction": "ولاية قضائية", "Operating model": "نموذج تشغيل", "Program": "برنامج", "Practice": "ممارسة",
    "Descriptive comparison": "مقارنة وصفية", "Qualitative assessment": "تقييم نوعي", "Checklist (yes / no)": "قائمة تحقق (نعم / لا)", "Maturity (0–4)": "النضج (0–4)",
    "Quantitative indicator": "مؤشر كمي", "Common practice (present / not evident)": "ممارسة شائعة (موجودة / غير ظاهرة)", "Leading practice (identified / not)": "ممارسة رائدة (محددة / لا)",
    "No framework yet. Generate one from the requirements, or start blank and build it yourself.": "لا يوجد إطار بعد. ولّده من المتطلبات أو ابدأ من الصفر وابنه بنفسك.",
    "Evidence base: benchmark × question": "قاعدة الأدلة: نموذج مقارن × سؤال", "Described": "موصوف", "Present": "موجودة", "Not evident": "غير ظاهرة",
    "Leading practice": "ممارسة رائدة", "Not identified": "غير محددة", "★ Leading practice": "★ ممارسة رائدة", "author": "المؤلف",
    "Comparison matrix": "مصفوفة المقارنة", "Comparison matrix with scores": "مصفوفة المقارنة مع الدرجات", "Method": "المنهج",
    "✓ Approve all": "✓ اعتماد الكل", "Items left pending": "عناصر بقيت معلّقة", "Reason": "السبب", "Close": "إغلاق",
    "These could not be approved automatically. Edit them, link accepted evidence, or reject them.": "تعذّر اعتمادها تلقائيًا. عدّلها أو اربطها بأدلة مقبولة أو ارفضها.",
    "Standard benchmarking report": "تقرير المقارنة المعيارية الموحّد",
    "Fixed structure, dynamic content. Only approved content is used; every material statement carries an APA in-text citation.":
      "هيكل ثابت ومحتوى متغيّر. يُستخدم المحتوى المعتمد فقط، وكل عبارة جوهرية تحمل استشهادًا نصيًا بنمط APA.",
    "Draft executive summary & conclusions": "صياغة الملخص التنفيذي والاستنتاجات", "Redraft executive summary & conclusions": "إعادة صياغة الملخص التنفيذي والاستنتاجات",
    "Report structure": "هيكل التقرير", "Introduction": "المقدمة", "Benchmarking Methodology": "منهجية المقارنة المعيارية", "Benchmark Models": "النماذج المقارنة",
    "Comparative Analysis": "التحليل المقارن", "Recommendations & Conclusions": "التوصيات والاستنتاجات", "Ready": "جاهز", "No approved content": "لا يوجد محتوى معتمد",
    "Brief, scope and key questions": "الموجز والنطاق والأسئلة الرئيسية", "Analysis method, framework, benchmark set and source policy": "منهج التحليل والإطار والنماذج المقارنة وسياسة المصادر",
    "Conclusions": "الاستنتاجات", "Drafted together with the executive summary.": "تُصاغ مع الملخص التنفيذي.", "Draft the executive summary from the approved content.": "صُغ الملخص التنفيذي من المحتوى المعتمد.",
    "APA 7 · generated from accepted evidence cited in approved content": "APA 7 · تُولَّد من الأدلة المقبولة المستشهد بها في المحتوى المعتمد",
    "Release checks": "فحوصات الإطلاق", "Source credibility": "مصداقية المصادر", "Evidence": "الأدلة", "Comparability": "قابلية المقارنة", "Citations": "الاستشهادات",
    "Analysis": "التحليل", "Unsupported claims & approval": "الادعاءات غير المدعومة والاعتماد", "✓ Passed": "✓ ناجح",
    "Fact supported only by supporting-grade sources (P3/P4) without a primary source": "حقيقة مدعومة بمصادر مساندة فقط (P3/P4) بدون مصدر أولي",
    "Cited source cannot form an APA reference (author/publisher, year or title missing)": "مصدر مستشهد به لا يكوّن مرجع APA (ينقصه المؤلف أو السنة أو العنوان)",
    "All changes are saved": "كل التغييرات محفوظة", "Analysis method saved": "تم حفظ منهج التحليل", "Included in scoring": "أُدرج في الدرجات",
    "Excluded from scoring": "استُبعد من الدرجات", "All criteria approved": "اعتُمدت كل المعايير",
    "Add at least one key question the client wants answered.": "أضف سؤالًا رئيسيًا واحدًا على الأقل يريد العميل إجابته.",
    "Give every approved benchmark a benchmark role.": "حدد دورًا لكل نموذج مقارن معتمد.",
    "Select the analysis method (qualitative, quantitative or mixed).": "اختر منهج التحليل (نوعي أو كمي أو مختلط).", "Draft the executive summary first.": "صُغ الملخص التنفيذي أولًا.",
    "Saves this stage, completes its gate when you are allowed to, and moves on": "يحفظ المرحلة ويكمل بوابتها إن كانت لديك الصلاحية وينتقل للتالية",
    "Saved. A consultant or the engagement lead completes this stage.": "تم الحفظ. يكمل هذه المرحلة مستشار أو قائد المشروع.",
    "Saved and approved — awaiting QA Lead co-sign": "تم الحفظ والاعتماد، بانتظار توقيع مسؤول الجودة",
    "APA in-text citation used in the report": "الاستشهاد النصي بنمط APA المستخدم في التقرير",
    "Remove all dimensions and criteria and start from a blank framework?": "حذف كل المحاور والمعايير والبدء بإطار فارغ؟", "Remove this benchmark?": "حذف هذا النموذج المقارن؟",
    "Approve every pending item in this stage that passes the evidence rules? Items that fail are left pending with the reason.": "اعتماد كل العناصر المعلّقة في هذه المرحلة التي تستوفي قواعد الأدلة؟ ما لا يستوفيها يبقى معلّقًا مع السبب.",
  };
  const P = [
    [/^Stage (\d)$/, "المرحلة $1"], [/^Task #(\d+)$/, "المهمة #$1"], [/^Evidence \((\d+)\)$/, "الأدلة ($1)"], [/^Search log \((\d+)\)$/, "سجل البحث ($1)"],
    [/^(\d+) items?$/, "$1 عنصر"], [/^Run AI research \((\d+) tasks\)$/, "تشغيل البحث بالذكاء الاصطناعي ($1 مهمة)"],
    [/^Lead: (.+)$/, "القائد: $1"], [/^Reviewed by (.+)$/, "راجعه $1"], [/^Reviewer \((.*)\): (.*)$/, "المراجع ($1): $2"],
    [/^Gate: (.+?)\s*$/, (m, g) => "البوابة: " + (D[g] || g) + " "], [/^Submit for “(.+)”$/, (m, g) => "إرسال لـ«" + (D[g] || g) + "»"],
    [/^🔒 (.*)$/, "🔒 $1"], [/^unlocks when the previous gate \(“(.+)”\) is approved\.$/, (m, g) => "تُفتح عند اعتماد البوابة السابقة («" + (D[g] || g) + "»)."],
    [/^(\d+) comparators · (\d+) criteria$/, "$1 نماذج مقارنة · $2 معايير"], [/^Research (\d+)\/(\d+) tasks$/, "البحث $1/$2 مهمة"],
    [/^(\d+) accepted evidence · (\d+) pending$/, "$1 أدلة مقبولة · $2 معلّقة"], [/^(\d+) approved content · (\d+) pending$/, "$1 محتوى معتمد · $2 معلّق"],
    [/^(\d+)\/(\d+) ev\.(.*)$/, (m, a, b, r) => `${a}/${b} أدلة` + r.replace(/· (\d+) to review/, "· $1 للمراجعة").replace(/· sufficient/, "· كافية").replace(/· partial/, "· جزئية").replace(/· conflict/, "· تعارض")],
    [/^Sufficiency: (\w+)$/, (m, s) => "الكفاية: " + (D[s] || s)], [/^Indicator: (.*)$/, "المؤشر: $1"], [/^Limitations: (.*)$/, "القيود: $1"],
    [/^accessed (.*)$/, "تاريخ الوصول $1"], [/^Notable practice: (.*)$/, "ممارسة بارزة: $1"], [/^Edit content item #(\d+)$/, "تعديل عنصر المحتوى #$1"],
    [/^v(\d+) · edited$/, "نسخة $1 · معدّل"], [/^v(\d+) · (.*)$/, "نسخة $1 · $2"], [/^Gates awaiting approval \((\d+)\)$/, "بوابات بانتظار الاعتماد ($1)"],
    [/^Evidence to review \((\d+)\)$/, "أدلة للمراجعة ($1)"], [/^Content to review \((\d+)\)$/, "محتوى للمراجعة ($1)"],
    [/^Weighted, normalised 0–100\. Composite shown only when coverage ≥ (\d+)%\. Overall coverage (\d+)%\.$/, "مرجّحة ومعيارية من 0 إلى 100. النتيجة المركبة تُعرض فقط عند تغطية ≥ $1%. التغطية الكلية $2%."],
    [/^(\d+) items · every accepted item carries publisher, date, locator and an archived excerpt$/, "$1 عنصر · كل دليل مقبول يحمل الناشر والتاريخ والموضع ومقتطفًا محفوظًا"],
    [/^Now acting as (.*?) \((.*)\)$/, (m, n, r) => "تعمل الآن بصفة " + n + " (" + (D[r] || r) + ")"],
    [/^● Claude live · (.*)$/, "● Claude مباشر · $1"], [/^visual: (.*)$/, "العرض: $1"], [/^(.*) · visual: (.*)$/, "$1 · العرض: $2"],
    [/^Cannot submit: (.*)$/, (m, r) => "لا يمكن الإرسال: " + r.split(/(?<=\.) /).map(x => D[x] || x).join(" ")],
    [/^(\d+) research task\(s\) not closed \(complete or gap\)\.$/, "$1 مهمة بحث غير مغلقة (مكتملة أو فجوة)."],
    [/^(\d+) evidence item\(s\) still awaiting review\.$/, "$1 دليل ما زال بانتظار المراجعة."], [/^(\d+) content item\(s\) still pending review\.$/, "$1 عنصر محتوى ما زال بانتظار المراجعة."],
    [/^(\d+) critical QA issue\(s\) block release\.$/, "$1 مشكلة جودة حرجة تمنع الإطلاق."],
    [/^Your role \((.*)\) cannot perform this action\.$/, "دورك ($1) لا يسمح بهذا الإجراء."], [/^Viewers have read-only access\.$/, "المشاهد له صلاحية القراءة فقط."],
    [/^Report section “(.+)” has no approved content\.$/, (m, x) => `قسم التقرير «${D[x] || x}» لا يحتوي محتوى معتمدًا.`],
    [/^(\d+) approved item\(s\)$/, "$1 عنصر معتمد"], [/^(\d+) APA references generated from cited evidence$/, "$1 مرجع APA مولّد من الأدلة المستشهد بها"],
    [/^(\d+) open issue\(s\)(?: · (\d+) critical)?$/, (m, a, b) => `${a} مشكلة مفتوحة` + (b ? ` · ${b} حرجة` : "")],
    [/^(\d+) item\(s\) approved(?: · (\d+) need attention)?$/, (m, a, b) => `اعتُمد ${a} عنصر` + (b ? ` · ${b} تحتاج مراجعة` : "")],
    [/^Saved\. To move on, first: (.*)$/, (m, x) => "تم الحفظ. للانتقال، أولًا: " + (D[x] || x)],
    [/^Saved · “(.+)” approved$/, (m, g) => `تم الحفظ · اعتُمدت «${D[g] || g}»`], [/^“(.+)” approved$/, (m, g) => `اعتُمدت «${D[g] || g}»`],
    [/^Saved and submitted — awaiting approval \((.*)\)$/, (m, r) => "تم الحفظ والإرسال، بانتظار الاعتماد (" + r.split(" / ").map(x => D[x] || x).join(" / ") + ")"],
    [/^Scores apply only to scored criteria.*coverage ≥ (\d+)%\. Score coverage (\d+)%\.$/, "الدرجات للمعايير المرجّحة فقط، من 0 إلى 100. النتيجة المركبة عند تغطية ≥ $1%. تغطية الدرجات $2%."],
    [/^No numerical scoring \((.*)\)\. Cells show the assessment for each method\. (\d+)% of cells assessed\.$/, (m, w, n) => `بدون درجات رقمية (${w === "qualitative analysis" ? "تحليل نوعي" : "أقل من معيارين مرجّحين"}). الخلايا تعرض التقييم حسب المنهج. تم تقييم ${n}% من الخلايا.`],
    [/^(.+) — no score; the response text is the assessment$/, (m, x) => `${D[x] || x}: بدون درجة؛ نص الإجابة هو التقييم`],
    [/^(.+) · wt (\d+)$/, (m, x, w) => `${D[x] || x} · الوزن ${w}`], [/^(.+) · not scored$/, (m, x) => `${D[x] || x} · بدون درجة`],
    [/^✦ AI recommendation: (.*)$/, "✦ توصية الذكاء الاصطناعي: $1"],

  ];
  let lang = "en";
  try { lang = localStorage.getItem("bs_lang") || "en"; } catch (e) { }
  window.BS_LANG = lang;
  const tr = s => {
    const k = s.trim();
    if (!k) return null;
    if (D[k] !== undefined) return s.replace(k, D[k]);
    for (const [re, rep] of P) if (re.test(k)) return s.replace(k, k.replace(re, rep));
    return null;
  };
  const SKIP = { PRE: 1, CODE: 1, SCRIPT: 1, STYLE: 1, TEXTAREA: 1 };
  function walk(node) {
    if (node.nodeType === 3) {
      const p = node.parentNode;
      if (!p || SKIP[p.tagName] || p.closest?.(".mono,.it-x,.quote")) return;
      const t = tr(node.nodeValue); if (t !== null) node.nodeValue = t; return;
    }
    if (node.nodeType !== 1 || SKIP[node.tagName]) return;
    for (const a of ["title", "placeholder"]) if (node.hasAttribute?.(a)) { const t = tr(node.getAttribute(a)); if (t !== null) node.setAttribute(a, t); }
    if (node.tagName === "INPUT" && node.type !== "text" && node.value) { const t = tr(node.value); if (t !== null) node.value = t; }
    for (const c of [...node.childNodes]) walk(c);
  }
  function mount() {
    const btn = document.createElement("button");
    btn.className = "btn sm"; btn.id = "langBtn"; btn.textContent = lang === "ar" ? "English" : "العربية"; btn.title = "Switch language";
    btn.onclick = () => { try { localStorage.setItem("bs_lang", lang === "ar" ? "en" : "ar"); } catch (e) { } location.reload(); };
    document.querySelector(".top-r")?.prepend(btn);
    if (lang !== "ar") return;
    document.documentElement.lang = "ar"; document.documentElement.dir = "rtl";
    if (!document.getElementById("arfont")) {
      const l = document.createElement("link"); l.id = "arfont"; l.rel = "stylesheet";
      l.href = "https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap"; document.head.appendChild(l);
    }
    walk(document.body);
    new MutationObserver(ms => { for (const m of ms) { if (m.type === "characterData") walk(m.target); else m.addedNodes.forEach(walk); } })
      .observe(document.body, { childList: true, subtree: true, characterData: true });
  }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", mount) : mount();
})();
