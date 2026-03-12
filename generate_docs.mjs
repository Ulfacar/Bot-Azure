import {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, Table, TableRow, TableCell, WidthType,
  PageBreak, ShadingType, TableOfContents
} from "docx";
import fs from "fs";

const BLUE = "00468C";
const GRAY = "646464";
const WHITE = "FFFFFF";
const LIGHT_BLUE = "D6E4F0";
const GREEN_BG = "E8F5E9";

function heading(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({ heading: level, spacing: { before: 300, after: 150 }, children: [new TextRun({ text })] });
}
function h2(text) { return heading(text, HeadingLevel.HEADING_2); }
function h3(text) { return heading(text, HeadingLevel.HEADING_3); }

function text(t, opts = {}) {
  return new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: t, size: 22, ...opts })] });
}

function bullet(t, opts = {}) {
  return new Paragraph({ bullet: { level: 0 }, spacing: { after: 80 }, children: [new TextRun({ text: t, size: 22, ...opts })] });
}

function numberedText(num, t) {
  return new Paragraph({ spacing: { after: 100 }, children: [
    new TextRun({ text: `${num}. `, bold: true, size: 22 }),
    new TextRun({ text: t, size: 22 }),
  ]});
}

function makeCell(t, opts = {}) {
  return new TableCell({
    shading: opts.header ? { type: ShadingType.SOLID, color: BLUE, fill: BLUE } : opts.green ? { type: ShadingType.SOLID, color: GREEN_BG, fill: GREEN_BG } : undefined,
    children: [new Paragraph({ children: [new TextRun({ text: t, size: 22, bold: !!opts.header, color: opts.header ? WHITE : undefined })] })],
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
  });
}

function emptyLine() {
  return new Paragraph({ spacing: { after: 100 }, children: [] });
}

// ========================
// DOCUMENT 1: КП (Commercial Proposal)
// ========================

const kp = new Document({
  sections: [{
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
        new TextRun({ text: "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ", size: 44, bold: true, color: BLUE })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
        new TextRun({ text: "AI-бот для отеля", size: 36, bold: true })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
        new TextRun({ text: "Telegram + WhatsApp ассистент", size: 28, color: GRAY })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [
        new TextRun({ text: "Подготовлено для отеля Ton Azure", size: 24, color: GRAY })
      ]}),

      // --- ЧТО МЫ ДЕЛАЕМ ---
      heading("1. Что мы делаем"),
      text("Разрабатываем умного AI-ассистента для отеля Ton Azure, который будет обрабатывать входящие запросы гостей через WhatsApp, Telegram и сайт отеля. Бот интегрируется с системой бронирования Exely, самостоятельно собирает данные клиента, формирует готовый лид и передаёт менеджеру на подтверждение."),
      emptyLine(),
      text("Результат: менеджер получает готовых клиентов с заполненными данными, а не сырые сообщения.", { bold: true }),

      // --- ЧТО ВХОДИТ ---
      heading("2. Что входит в проект"),

      h2("AI-бот (WhatsApp + Telegram + сайт)"),
      bullet("Умный ассистент на базе нейросети — отвечает на вопросы гостей 24/7"),
      bullet("Каналы: WhatsApp, Telegram, виджет на сайте отеля"),
      bullet("Интеграция с системой бронирования Exely — бот видит наличие номеров"),
      bullet("Собирает данные клиента: даты заезда/выезда, количество гостей, копия паспорта, контакты"),
      bullet("Формирует готовый лид и отправляет менеджеру"),
      bullet("Если не знает ответ — говорит «уточню у менеджера» и передаёт диалог"),
      bullet("Работает на русском, кыргызском, английском и любом другом языке"),
      bullet("Никогда не выдумывает — отвечает строго по базе знаний"),

      h2("Единая панель управления (веб)"),
      bullet("Все диалоги из WhatsApp, Telegram и сайта в одном месте"),
      bullet("Менеджер видит готовые лиды, подтверждает/отклоняет"),
      bullet("Менеджер может перехватить диалог и общаться с клиентом напрямую"),
      bullet("Уведомления на телефон менеджера о новых заявках"),
      bullet("Бот отправляет клиенту подтверждение брони после одобрения менеджером"),

      h2("База знаний + самообучение"),
      bullet("Менеджер может обучить бота прямо из панели — добавить вопрос и ответ"),
      bullet("Бот запоминает ответы менеджера и использует повторно"),
      bullet("Чем дольше работает — тем меньше вопросов к менеджеру"),

      h2("Статистика"),
      bullet("Количество обработанных клиентов"),
      bullet("Расход токенов AI за период"),
      bullet("Статусы диалогов: новые, в работе, закрытые"),

      // --- ПРОЦЕСС РАБОТЫ БОТА ---
      heading("3. Как работает бот (клиентский путь)"),
      emptyLine(),
      numberedText(1, "Гость пишет в WhatsApp или Telegram"),
      numberedText(2, "Бот приветствует, рассказывает об отеле, отвечает на вопросы"),
      numberedText(3, "Гость хочет забронировать → бот собирает: даты, кол-во гостей, паспорт, контакт"),
      numberedText(4, "Бот подтверждает получение данных и говорит «уточняю у менеджера»"),
      numberedText(5, "Менеджер получает уведомление → видит готовый лид в панели"),
      numberedText(6, "Менеджер подтверждает → бот отправляет клиенту: «Бронь подтверждена! Заезд такого-то, выезд такого-то»"),
      numberedText(7, "Если что-то не так — менеджер перехватывает диалог и решает вопрос лично"),
      emptyLine(),
      text("Если бот не понимает вопрос → сообщает клиенту «мне нужно уточнить у менеджера, вернусь в ближайшее время» → менеджер может ответить и обучить бота на этой теме.", { italics: true }),

      // --- СТОИМОСТЬ ---
      heading("4. Стоимость"),
      emptyLine(),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({ children: [makeCell("Услуга", { header: true, width: 60 }), makeCell("Стоимость", { header: true, width: 40 })] }),
          new TableRow({ children: [makeCell("Разработка AI-бота (WhatsApp + Telegram) + единая панель + настройка + запуск", { width: 60 }), makeCell("$700 (разовая оплата)", { width: 40 })] }),
          new TableRow({ children: [makeCell("Техподдержка и сопровождение", { width: 60 }), makeCell("3 месяца — включено", { width: 40 })] }),
          new TableRow({ children: [makeCell("Облачный сервер и база данных (ежемесячно)", { width: 60 }), makeCell("~$5-7/мес (~450-600 сом)", { width: 40 })] }),
          new TableRow({ children: [makeCell("AI-токены / нейросеть (ежемесячно)", { width: 60 }), makeCell("~$5-10/мес (~450-850 сом)", { width: 40 })] }),
          new TableRow({ children: [makeCell("ИТОГО ежемесячно", { width: 60, green: true }), makeCell("~850-1450 сом/мес (~$10-17)", { width: 40, green: true })] }),
        ]
      }),
      emptyLine(),
      text("После 3 месяцев — отдельный договор на техподдержку (по договорённости).", { italics: true }),

      // --- ЧТО ВХОДИТ В $700 ---
      heading("5. Что входит в $700"),
      bullet("Полная разработка AI-бота под ваш отель"),
      bullet("Подключение WhatsApp + Telegram"),
      bullet("Веб-панель управления для менеджера"),
      bullet("Настройка базы знаний по вашим ответам"),
      bullet("Обучение администратора работе с панелью"),
      bullet("3 месяца техподдержки и сопровождения (апрель — июнь)"),
      bullet("Все доработки в рамках согласованного ТЗ"),
      bullet("Все наработки, код и данные переходят вам"),

      // --- СРОКИ ---
      heading("6. Сроки"),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({ children: [makeCell("Этап", { header: true, width: 50 }), makeCell("Срок", { header: true, width: 25 }), makeCell("Описание", { header: true, width: 25 })] }),
          new TableRow({ children: [makeCell("Получение опросника и ТЗ"), makeCell("День 1"), makeCell("Вы заполняете опросник")] }),
          new TableRow({ children: [makeCell("Разработка и настройка"), makeCell("День 2-5"), makeCell("Создаём бота, панель, подключаем")] }),
          new TableRow({ children: [makeCell("MVP и тестирование"), makeCell("День 6-7"), makeCell("Вы тестируете, даёте обратную связь")] }),
          new TableRow({ children: [makeCell("Запуск"), makeCell("День 7-8"), makeCell("Бот работает для реальных клиентов")] }),
        ]
      }),

      // --- ГАРАНТИИ ---
      heading("7. Гарантии"),
      bullet("Все данные (диалоги, контакты, база знаний) — ваша собственность"),
      bullet("Код проекта может быть передан вам"),
      bullet("3 месяца мы следим за проектом — любые баги исправляем бесплатно"),
      bullet("Бот обучается на вашем бизнесе — чем дольше работает, тем лучше"),

      // --- ДАЛЬНЕЙШЕЕ РАЗВИТИЕ ---
      heading("8. Дальнейшее развитие (следующие этапы)"),
      text("После запуска базового решения доступны дополнительные интеграции и расширения функционала:"),
      emptyLine(),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({ children: [makeCell("Модуль", { header: true, width: 50 }), makeCell("Описание", { header: true, width: 30 }), makeCell("Стоимость", { header: true, width: 20 })] }),
          new TableRow({ children: [makeCell("Интеграция с Exely"), makeCell("Бот видит свободные номера в реальном времени, передаёт бронь в систему"), makeCell("по договорённости")] }),
          new TableRow({ children: [makeCell("Виджет чата на сайт"), makeCell("Гости общаются с ботом прямо на сайте отеля, без перехода в мессенджер"), makeCell("по договорённости")] }),
          new TableRow({ children: [makeCell("Автосбор документов"), makeCell("Бот запрашивает и принимает копию паспорта, формирует готовый лид с документами"), makeCell("по договорённости")] }),
          new TableRow({ children: [makeCell("Автоподтверждение брони"), makeCell("После одобрения менеджером — бот сам отправляет клиенту подтверждение с деталями заезда"), makeCell("по договорённости")] }),
          new TableRow({ children: [makeCell("Расширенная аналитика"), makeCell("Детальная статистика: конверсия, популярные вопросы, загрузка по каналам"), makeCell("по договорённости")] }),
        ]
      }),
      emptyLine(),
      text("Каждый модуль подключается отдельно по мере необходимости. Все интеграции обсуждаются индивидуально.", { italics: true }),

      // --- СЛЕДУЮЩИЕ ШАГИ ---
      heading("9. Следующие шаги"),
      numberedText(1, "Вы заполняете опросник (информация об отеле для бота)"),
      numberedText(2, "Мы согласовываем ТЗ"),
      numberedText(3, "Оплата → начинаем разработку"),
      numberedText(4, "Через неделю — готовый MVP для тестирования"),
      emptyLine(),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 }, children: [
        new TextRun({ text: "Asystem", size: 28, bold: true, color: BLUE })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "+996 500 115 133  |  @Ruslyandi", size: 22, color: GRAY })
      ]}),
    ]
  }]
});

// ========================
// DOCUMENT 2: ТЗ (Technical Specification)
// ========================

const tz = new Document({
  sections: [{
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
        new TextRun({ text: "ТЕХНИЧЕСКОЕ ЗАДАНИЕ", size: 44, bold: true, color: BLUE })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
        new TextRun({ text: "AI-бот для отеля", size: 36, bold: true })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [
        new TextRun({ text: "Версия 1.0 | Март 2026", size: 22, color: GRAY })
      ]}),

      // 1. ОБЩЕЕ ОПИСАНИЕ
      heading("1. Общее описание проекта"),
      text("Разработка AI-ассистента для отеля Ton Azure, который автоматизирует обработку входящих обращений гостей через WhatsApp, Telegram и виджет на сайте отеля. С интеграцией в систему бронирования Exely."),
      emptyLine(),
      text("Цель: автоматизировать сбор данных от клиентов, сформировать готовый лид и передать менеджеру на подтверждение. Снизить нагрузку на персонал и исключить потерю клиентов."),

      // 2. ФУНКЦИОНАЛ БОТА
      heading("2. Функциональные требования"),

      h2("2.1. AI-ассистент (чат-бот)"),
      bullet("Автоматические ответы на вопросы гостей на основе базы знаний"),
      bullet("Поддержка русского, кыргызского, английского и других языков"),
      bullet("Сбор данных для бронирования: даты заезда/выезда, количество гостей, ФИО, контактный телефон, копия паспорта"),
      bullet("Формирование готового лида и передача менеджеру"),
      bullet("Отправка подтверждения брони клиенту после одобрения менеджером"),
      bullet("Тег [НУЖЕН_МЕНЕДЖЕР] — автоматическое подключение менеджера, когда бот не может ответить"),
      bullet("Бот сообщает клиенту: «Мне нужно уточнить у менеджера, вернусь в ближайшее время»"),
      bullet("Никогда не выдумывает информацию — отвечает только по базе знаний"),
      bullet("Тёплый, вежливый тон общения"),

      h2("2.2. Каналы связи"),
      h3("WhatsApp"),
      bullet("Интеграция через wapi.pro (сторонний сервис) или Meta Business API"),
      bullet("Приём текстовых сообщений и изображений (копия паспорта)"),
      bullet("Отправка текстовых ответов клиентам"),

      h3("Telegram"),
      bullet("Бот на базе Aiogram 3 (polling)"),
      bullet("Приём текстовых сообщений и фото"),
      bullet("Кнопки и меню для навигации"),
      bullet("Уведомления менеджеру с кнопками «Ответить» / «История»"),

      h3("Сайт отеля"),
      bullet("Виджет чата на существующем сайте отеля"),
      bullet("Гость общается с ботом прямо на сайте без перехода в мессенджер"),
      bullet("Все диалоги попадают в единую панель управления"),

      h2("2.3. Интеграция с Exely (система бронирования)"),
      bullet("Подключение к API Exely для проверки наличия свободных номеров"),
      bullet("Бот может сообщить гостю о доступности номеров на запрашиваемые даты"),
      bullet("Данные бронирования передаются в Exely после подтверждения менеджером"),

      h2("2.4. Единая панель управления (веб-интерфейс)"),
      bullet("Авторизация по логину и паролю (JWT)"),
      bullet("Список всех диалогов с фильтрацией по статусу и каналу (WhatsApp/Telegram)"),
      bullet("Просмотр истории переписки с клиентом"),
      bullet("Менеджер может отправить сообщение клиенту прямо из панели"),
      bullet("Менеджер может перехватить диалог у бота в любой момент"),
      bullet("Подтверждение/отклонение заявки на бронирование"),
      bullet("Уведомления о новых лидах (push/Telegram)"),

      h2("2.5. База знаний и самообучение"),
      bullet("CRUD-интерфейс для управления вопросами и ответами"),
      bullet("Менеджер может добавить новый вопрос-ответ через панель"),
      bullet("Кнопка «Обучить» — бот запоминает ответ менеджера на конкретную тему"),
      bullet("Автосохранение ответов менеджера при закрытии диалога"),
      bullet("Поиск по ключевым словам с fuzzy-matching"),
      bullet("Счётчик использования каждой записи"),

      h2("2.6. Статистика"),
      bullet("Количество диалогов за период (день/неделя/месяц)"),
      bullet("Количество готовых лидов"),
      bullet("Статусы: в работе, ожидает менеджера, закрыт"),
      bullet("Расход AI-токенов за период"),

      h2("2.7. Уведомления"),
      bullet("Уведомление менеджеру в Telegram при новом лиде"),
      bullet("Уведомление менеджеру, когда бот не может ответить"),
      bullet("Подтверждение брони клиенту после одобрения менеджером"),

      // 3. КЛИЕНТСКИЙ ПУТЬ
      heading("3. Сценарий работы (клиентский путь)"),
      emptyLine(),

      h2("Сценарий 1: Успешное бронирование"),
      numberedText(1, "Клиент пишет в WhatsApp/Telegram"),
      numberedText(2, "Бот приветствует, спрашивает чем помочь"),
      numberedText(3, "Клиент интересуется номерами → бот отвечает по базе знаний"),
      numberedText(4, "Клиент хочет забронировать → бот запрашивает: даты, кол-во гостей, ФИО, телефон, копию паспорта"),
      numberedText(5, "Клиент предоставляет данные → бот подтверждает получение"),
      numberedText(6, "Бот формирует лид → отправляет менеджеру в панель + уведомление в Telegram"),
      numberedText(7, "Менеджер проверяет данные → нажимает «Подтвердить»"),
      numberedText(8, "Бот отправляет клиенту: «Бронь подтверждена! Заезд: [дата], Выезд: [дата]. Ждём вас!»"),

      h2("Сценарий 2: Бот не знает ответ"),
      numberedText(1, "Клиент задаёт вопрос, которого нет в базе знаний"),
      numberedText(2, "Бот: «Мне необходимо уточнить эти детали у менеджера. Вернусь в ближайшее время»"),
      numberedText(3, "Менеджер получает уведомление → отвечает клиенту"),
      numberedText(4, "Менеджер нажимает «Обучить» → ответ сохраняется в базу знаний"),
      numberedText(5, "В следующий раз бот ответит на этот вопрос сам"),

      h2("Сценарий 3: Менеджер перехватывает диалог"),
      numberedText(1, "Менеджер видит диалог в панели и хочет ответить лично"),
      numberedText(2, "Нажимает «Перехватить» → бот прекращает отвечать"),
      numberedText(3, "Менеджер общается с клиентом напрямую через панель"),
      numberedText(4, "По завершении — закрывает диалог, ответы сохраняются в базу"),

      // 4. ТЕХНИЧЕСКАЯ АРХИТЕКТУРА
      heading("4. Техническая архитектура"),
      emptyLine(),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({ children: [makeCell("Компонент", { header: true, width: 30 }), makeCell("Технология", { header: true, width: 30 }), makeCell("Описание", { header: true, width: 40 })] }),
          new TableRow({ children: [makeCell("Backend"), makeCell("Python, FastAPI"), makeCell("API, логика бота, обработка сообщений")] }),
          new TableRow({ children: [makeCell("Telegram бот"), makeCell("Aiogram 3"), makeCell("Polling, кнопки, уведомления менеджеру")] }),
          new TableRow({ children: [makeCell("WhatsApp бот"), makeCell("wapi.pro / Meta API"), makeCell("Вебхуки, приём/отправка сообщений")] }),
          new TableRow({ children: [makeCell("Виджет на сайт"), makeCell("JavaScript widget"), makeCell("Чат-виджет на существующем сайте отеля")] }),
          new TableRow({ children: [makeCell("Система бронирования"), makeCell("Exely API"), makeCell("Проверка наличия номеров, передача броней")] }),
          new TableRow({ children: [makeCell("AI-движок"), makeCell("OpenRouter (DeepSeek V3)"), makeCell("Генерация ответов, понимание контекста")] }),
          new TableRow({ children: [makeCell("База данных"), makeCell("PostgreSQL (Neon)"), makeCell("Клиенты, диалоги, сообщения, база знаний")] }),
          new TableRow({ children: [makeCell("Frontend"), makeCell("React + Vite"), makeCell("Веб-панель управления")] }),
          new TableRow({ children: [makeCell("Хостинг backend"), makeCell("Railway"), makeCell("Облачный сервер с автоперезапуском")] }),
          new TableRow({ children: [makeCell("Хостинг frontend"), makeCell("Vercel"), makeCell("Статический хостинг панели")] }),
        ]
      }),

      // 5. ТРЕБОВАНИЯ К ЗАКАЗЧИКУ
      heading("5. Требования к заказчику"),
      text("Для запуска проекта необходимо предоставить:"),
      bullet("Заполненный опросник (информация об отеле, номерах, услугах, правилах)"),
      bullet("Telegram-аккаунт менеджера (для уведомлений)"),
      bullet("Номер телефона для WhatsApp-бота (отдельная SIM-карта)"),
      bullet("Доступ к Facebook/Meta Business аккаунту (если есть) или согласие на подключение через wapi.pro"),
      bullet("Доступ к аккаунту Exely (для интеграции с системой бронирования)"),
      bullet("Доступ к сайту отеля (для установки виджета чата)"),
      bullet("Обратная связь в течение тестирования (2-3 дня)"),

      // 6. СРОКИ
      heading("6. Сроки реализации"),
      text("Общий срок: 7-8 рабочих дней с момента получения заполненного опросника и оплаты."),
      emptyLine(),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({ children: [makeCell("Этап", { header: true }), makeCell("Срок", { header: true }), makeCell("Результат", { header: true })] }),
          new TableRow({ children: [makeCell("Согласование ТЗ и опросника"), makeCell("День 1"), makeCell("Утверждённое ТЗ, заполненный опросник")] }),
          new TableRow({ children: [makeCell("Разработка backend + AI"), makeCell("День 2-3"), makeCell("Работающий бот с базой знаний")] }),
          new TableRow({ children: [makeCell("Разработка панели"), makeCell("День 3-4"), makeCell("Веб-панель для менеджера")] }),
          new TableRow({ children: [makeCell("Подключение WhatsApp + Telegram"), makeCell("День 4-5"), makeCell("Бот работает в обоих каналах")] }),
          new TableRow({ children: [makeCell("Тестирование"), makeCell("День 6-7"), makeCell("Заказчик тестирует, обратная связь")] }),
          new TableRow({ children: [makeCell("Запуск"), makeCell("День 7-8"), makeCell("Бот работает для реальных клиентов")] }),
        ]
      }),

      // 7. СТОИМОСТЬ
      heading("7. Стоимость и условия оплаты"),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({ children: [makeCell("Позиция", { header: true, width: 60 }), makeCell("Сумма", { header: true, width: 40 })] }),
          new TableRow({ children: [makeCell("Разработка + настройка + запуск (WhatsApp + Telegram)"), makeCell("$700 (разово)")] }),
          new TableRow({ children: [makeCell("Техподдержка"), makeCell("3 месяца — включено")] }),
          new TableRow({ children: [makeCell("Облачный сервер и база данных (ежемесячно)"), makeCell("~$5-7/мес (~450-600 сом)")] }),
          new TableRow({ children: [makeCell("AI-токены / нейросеть (ежемесячно)"), makeCell("~$5-10/мес (~450-850 сом)")] }),
          new TableRow({ children: [makeCell("ИТОГО ежемесячно"), makeCell("~850-1450 сом/мес (~$10-17)")] }),
        ]
      }),
      emptyLine(),
      bullet("Все наработки, код и данные переходят заказчику"),
      bullet("После 3 месяцев — отдельный договор на техподдержку по договорённости"),
      bullet("Дополнительные доработки за рамками ТЗ — оцениваются отдельно"),

      // 8. ПРИЁМКА
      heading("8. Порядок приёмки"),
      numberedText(1, "Заказчик тестирует MVP в течение 2-3 дней"),
      numberedText(2, "Замечания фиксируются и исправляются"),
      numberedText(3, "После устранения замечаний — подписание акта приёмки"),
      numberedText(4, "Начало 3-месячного периода техподдержки"),

      emptyLine(),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 }, children: [
        new TextRun({ text: "Asystem  |  +996 500 115 133  |  @Ruslyandi", size: 22, color: GRAY })
      ]}),
    ]
  }]
});

// ========================
// DOCUMENT 3: ОПРОСНИК
// ========================

const questions = [
  { category: "1. Общая информация об отеле", items: [
    "Полное название отеля",
    "Адрес отеля (город, улица, ориентиры)",
    "Как добраться до отеля? (описание маршрута, ближайшие ориентиры)",
    "Краткое описание отеля (2-3 предложения, чем уникален, что отличает от других)",
    "Категория/класс отеля (звёзды, если есть)",
    "Год открытия / после последнего ремонта",
    "Контактный телефон для гостей",
    "Контактный email",
    "Instagram / соцсети отеля",
    "Сайт отеля (если есть)",
  ]},
  { category: "2. Номера и размещение", items: [
    "Какие типы номеров есть? (стандарт, люкс, семейный и т.д.) — перечислите все",
    "Сколько номеров каждого типа?",
    "Описание каждого типа номера (площадь, кровати, вид из окна)",
    "Что входит в номер? (Wi-Fi, ТВ, кондиционер, мини-бар, сейф, фен, халат и т.д.)",
    "Максимальное количество гостей в каждом типе номера",
    "Есть ли номера для людей с ограниченными возможностями?",
    "Есть ли семейные номера / номера с детской кроваткой?",
    "Цены на номера (за сутки, за сезон/не сезон, если отличаются)",
    "Есть ли скидки (раннее бронирование, длительное проживание, группы)?",
  ]},
  { category: "3. Бронирование и заселение", items: [
    "Время заезда (check-in)",
    "Время выезда (check-out)",
    "Возможен ли ранний заезд / поздний выезд? Условия?",
    "Какие документы нужны при заселении? (паспорт, удостоверение)",
    "Нужна ли предоплата? Какой процент?",
    "Способы оплаты (наличные, карта, QR, перевод)",
    "Политика отмены бронирования (за сколько дней, штрафы)",
    "Можно ли забронировать без предоплаты?",
    "Есть ли залог при заселении?",
    "Принимаете ли иностранных гостей? Нужна ли регистрация?",
  ]},
  { category: "4. Услуги отеля", items: [
    "Есть ли завтрак? Входит ли в стоимость? Время завтрака?",
    "Есть ли ресторан / кафе на территории? Меню?",
    "Есть ли room-service?",
    "Есть ли парковка? Бесплатная или платная?",
    "Есть ли Wi-Fi? Бесплатный?",
    "Есть ли трансфер из/в аэропорт? Стоимость?",
    "Есть ли прачечная / химчистка?",
    "Есть ли бассейн / сауна / спа / хамам?",
    "Есть ли тренажёрный зал / фитнес?",
    "Есть ли конференц-зал / банкетный зал? Вместимость?",
    "Есть ли детская площадка / игровая комната?",
    "Есть ли экскурсии / развлечения? Какие?",
    "Есть ли прокат (велосипеды, лодки, оборудование и т.д.)?",
    "Какие дополнительные платные услуги есть?",
  ]},
  { category: "5. Правила отеля", items: [
    "Можно ли с домашними животными? Условия?",
    "Можно ли курить? Есть ли зона для курения?",
    "Есть ли ограничения по шуму (тихий час)?",
    "Правила пользования бассейном / сауной (если есть)",
    "Есть ли возрастные ограничения для заселения?",
    "Политика в отношении третьих лиц / посещения гостей",
    "Что делать в случае потери ключа / карты?",
    "Есть ли правила по количеству людей в номере?",
  ]},
  { category: "6. Расположение и окрестности", items: [
    "Расстояние до центра города / основных достопримечательностей",
    "Расстояние до аэропорта / вокзала",
    "Что интересного рядом? (озеро, горы, рынок, магазины)",
    "Есть ли рядом аптека / банкомат / магазин?",
    "Расстояние до пляжа (если на Иссык-Куле)",
  ]},
  { category: "7. Сезонность и загрузка", items: [
    "Когда высокий сезон? Когда низкий?",
    "Отличаются ли цены в сезон / не сезон?",
    "Работает ли отель круглый год?",
    "В какие месяцы больше всего загрузка?",
    "Есть ли специальные предложения в низкий сезон?",
  ]},
  { category: "8. Особые случаи и мероприятия", items: [
    "Можно ли провести свадьбу / банкет / корпоратив? Условия?",
    "Есть ли специальные пакеты (романтический, семейный, тур)?",
    "Есть ли подарочные сертификаты?",
    "Есть ли программа лояльности / скидки для постоянных гостей?",
    "Работаете ли с турагентствами / корпоративными клиентами?",
  ]},
  { category: "9. Безопасность и экстренные ситуации", items: [
    "Есть ли круглосуточная охрана / видеонаблюдение?",
    "Есть ли сейф на ресепшн / в номерах?",
    "Что делать гостю в экстренной ситуации? (врач, пожар)",
    "Есть ли аптечка первой помощи?",
  ]},
  { category: "10. Для бота — тон и стиль", items: [
    "Как бот должен обращаться к гостям — на «вы» или «ты»?",
    "Какой тон: деловой, дружелюбный, премиальный?",
    "Есть ли слова/фразы, которые бот НЕ должен использовать?",
    "Должен ли бот использовать эмодзи?",
    "Есть ли фирменное приветствие / прощание?",
    "Какие вопросы бот должен ВСЕГДА передавать менеджеру? (кроме цен)",
  ]},
];

const oprosnikChildren = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
    new TextRun({ text: "ОПРОСНИК ДЛЯ ОТЕЛЯ", size: 44, bold: true, color: BLUE })
  ]}),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
    new TextRun({ text: "Заполните для настройки AI-бота", size: 28, color: GRAY })
  ]}),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [
    new TextRun({ text: "Ответы на эти вопросы станут базой знаний бота. Чем подробнее — тем лучше бот будет отвечать гостям.", size: 22, italics: true })
  ]}),
];

let questionNum = 1;
for (const section of questions) {
  oprosnikChildren.push(heading(section.category));
  oprosnikChildren.push(emptyLine());

  for (const q of section.items) {
    oprosnikChildren.push(new Paragraph({
      spacing: { after: 60 },
      children: [
        new TextRun({ text: `${questionNum}. ${q}`, bold: true, size: 22 })
      ]
    }));
    oprosnikChildren.push(new Paragraph({
      spacing: { after: 200 },
      shading: { type: ShadingType.SOLID, color: "F5F5F5", fill: "F5F5F5" },
      children: [
        new TextRun({ text: "Ответ: _______________________________________________", size: 22, color: GRAY })
      ]
    }));
    questionNum++;
  }
}

oprosnikChildren.push(emptyLine());
oprosnikChildren.push(new Paragraph({
  spacing: { before: 300 },
  shading: { type: ShadingType.SOLID, color: LIGHT_BLUE, fill: LIGHT_BLUE },
  children: [new TextRun({
    text: "Если вы не знаете ответ на какой-то вопрос — оставьте пустым или напишите «уточню». Мы поможем сформулировать.",
    italics: true, size: 22
  })]
}));

oprosnikChildren.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 }, children: [
  new TextRun({ text: "Asystem  |  +996 500 115 133  |  @Ruslyandi", size: 22, color: GRAY })
]}));

const oprosnik = new Document({ sections: [{ children: oprosnikChildren }] });

// ========================
// SAVE ALL THREE
// ========================

const desktop = "C:\\Users\\alanb\\OneDrive\\Рабочий стол\\";

const buf1 = await Packer.toBuffer(kp);
fs.writeFileSync(desktop + "КП_Ton_Azure.docx", buf1);
console.log("1. КП saved");

const buf2 = await Packer.toBuffer(tz);
fs.writeFileSync(desktop + "ТЗ_Ton_Azure.docx", buf2);
console.log("2. ТЗ saved");

const buf3 = await Packer.toBuffer(oprosnik);
fs.writeFileSync(desktop + "Опросник_Ton_Azure.docx", buf3);
console.log("3. Опросник saved");

console.log("All done!");
