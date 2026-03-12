import {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, Table, TableRow, TableCell, WidthType,
  PageBreak, ShadingType
} from "docx";
import fs from "fs";

const BLUE = "00468C";
const GRAY = "646464";
const WHITE = "FFFFFF";
const LIGHT_BLUE = "D6E4F0";
const RED_BG = "FDE8E8";

function heading(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({ heading: level, children: [new TextRun({ text })] });
}

function text(t, opts = {}) {
  return new Paragraph({
    spacing: { after: 120 },
    children: [new TextRun({ text: t, size: 22, ...opts })]
  });
}

function bullet(t) {
  return new Paragraph({
    bullet: { level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text: t, size: 22 })]
  });
}

function featureItem(title, desc) {
  return new Paragraph({
    spacing: { after: 100 },
    children: [
      new TextRun({ text: `✓ ${title}`, bold: true, size: 22 }),
      new TextRun({ text: ` — ${desc}`, size: 22 }),
    ]
  });
}

function makeCell(t, opts = {}) {
  return new TableCell({
    shading: opts.header ? { type: ShadingType.SOLID, color: BLUE, fill: BLUE } : undefined,
    children: [new Paragraph({
      children: [new TextRun({
        text: t, size: 22, bold: !!opts.header,
        color: opts.header ? WHITE : undefined
      })]
    })],
    width: { size: 50, type: WidthType.PERCENTAGE },
  });
}

function qaBlock(question, answer) {
  return [
    new Paragraph({
      spacing: { before: 200, after: 80 },
      children: [new TextRun({ text: question, bold: true, size: 24, color: BLUE })]
    }),
    new Paragraph({
      spacing: { after: 200 },
      children: [new TextRun({ text: answer, size: 22 })]
    }),
  ];
}

function qaBlockRed(question, answer) {
  return [
    new Paragraph({
      spacing: { before: 200, after: 80 },
      children: [new TextRun({ text: question, bold: true, size: 24, color: "CC0000" })]
    }),
    new Paragraph({
      spacing: { after: 200 },
      shading: { type: ShadingType.SOLID, color: RED_BG, fill: RED_BG },
      children: [new TextRun({ text: answer, size: 22 })]
    }),
  ];
}

const doc = new Document({
  sections: [
    {
      children: [
        // TITLE
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 100 },
          children: [new TextRun({ text: "AI-бот для отеля", size: 52, bold: true, color: BLUE })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 400 },
          children: [new TextRun({ text: "Telegram + WhatsApp ассистент для гостей", size: 28, color: GRAY })]
        }),

        // ЧТО ЭТО
        heading("Что это?"),
        text("Умный AI-ассистент, который отвечает гостям вашего отеля 24/7 в Telegram и WhatsApp. Бот берёт на себя рутинные вопросы, а когда нужно — мгновенно подключает менеджера."),

        // ФУНКЦИОНАЛ
        heading("Что умеет бот"),
        featureItem("Отвечает на вопросы гостей", "Номера, услуги, расположение, Wi-Fi, трансфер, правила заезда/выезда и т.д."),
        featureItem("Telegram + WhatsApp", "Работает в обоих мессенджерах — там, где уже сидят ваши клиенты."),
        featureItem("3 языка", "Русский, кыргызский, английский — бот автоматически подстраивается."),
        featureItem("Не врёт про цены", "Если вопрос про деньги — сразу подключает менеджера. Никогда не выдумывает."),
        featureItem("Самообучение", "Запоминает ответы менеджера и использует их повторно. Чем дольше работает — тем умнее."),
        featureItem("Уведомления менеджеру", "Когда бот не может ответить — менеджер получает уведомление в Telegram."),
        featureItem("Работает 24/7", "Ночью, в выходные, в праздники — бот всегда на связи."),

        // ВЕБ-ПАНЕЛЬ
        heading("Веб-панель управления"),
        text("Удобный интерфейс для менеджеров отеля:"),
        bullet("Все диалоги с гостями в одном месте"),
        bullet("Менеджер может отвечать гостям прямо из панели"),
        bullet("База знаний — добавляйте и редактируйте ответы бота"),
        bullet("Статистика обращений — сколько вопросов, какие темы"),
        bullet("Фильтрация по статусу — новые, в работе, закрытые"),

        // СРАВНЕНИЕ
        heading("Зачем это отелю"),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({ children: [makeCell("Без бота", { header: true }), makeCell("С ботом", { header: true })] }),
            new TableRow({ children: [makeCell("Менеджер отвечает на одни и те же вопросы"), makeCell("Бот закрывает 70-80% типовых вопросов")] }),
            new TableRow({ children: [makeCell("Гость ждёт ответа минуты/часы"), makeCell("Ответ мгновенно, за секунды")] }),
            new TableRow({ children: [makeCell("Потерянные заявки ночью и в выходные"), makeCell("Бот работает 24/7 без перерывов")] }),
            new TableRow({ children: [makeCell("Переписки в разных чатах"), makeCell("Единая панель + история + аналитика")] }),
          ]
        }),

        // КАК РАБОТАЕТ
        heading("Как это работает"),
        text("1. Гость пишет в Telegram или WhatsApp"),
        text("2. AI-бот отвечает за несколько секунд"),
        text("3. Если вопрос сложный — менеджер получает уведомление и подключается"),
        text("4. Ответ менеджера сохраняется — в следующий раз бот ответит сам"),

        // БРОНИРОВАНИЕ
        heading("Интеграция с системой бронирования"),
        text("Бот подключается к вашей существующей системе учёта номеров:"),
        new Paragraph({
          spacing: { after: 100 },
          children: [
            new TextRun({ text: "• Google Календарь: ", bold: true, size: 22 }),
            new TextRun({ text: "Бот видит свободные даты. Вы ведёте учёт как обычно.", size: 22 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 100 },
          children: [
            new TextRun({ text: "• Excel / тетрадка: ", bold: true, size: 22 }),
            new TextRun({ text: "Сделаем удобную панель — менеджер отмечает занятость, бот отвечает сам.", size: 22 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 100 },
          children: [
            new TextRun({ text: "• Booking.com / Airbnb: ", bold: true, size: 22 }),
            new TextRun({ text: "Бот подтягивает календарь занятости и понимает, какие даты свободны.", size: 22 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 100 },
          children: [
            new TextRun({ text: "• 1С / Opera / своя CRM: ", bold: true, size: 22 }),
            new TextRun({ text: "Подключаемся через API. Бот работает полностью автономно.", size: 22 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200 },
          children: [
            new TextRun({ text: "На старте бот уже работает ", size: 22 }),
            new TextRun({ text: "без интеграции", bold: true, size: 22 }),
            new TextRun({ text: " — просто передаёт заявки менеджеру. Интеграция подключается следующим этапом.", size: 22 }),
          ]
        }),

        // СРОКИ
        heading("Сроки запуска"),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({ children: [makeCell("Этап", { header: true }), makeCell("Срок", { header: true })] }),
            new TableRow({ children: [makeCell("Настройка и запуск бота"), makeCell("1-2 дня")] }),
            new TableRow({ children: [makeCell("Подключение Telegram"), makeCell("моментально")] }),
            new TableRow({ children: [makeCell("Подключение WhatsApp"), makeCell("1-3 дня")] }),
            new TableRow({ children: [makeCell("Интеграция с бронированием"), makeCell("по договорённости")] }),
          ]
        }),

        // ЧТО НУЖНО
        heading("Что нужно от вас для запуска"),
        bullet("Название отеля, адрес, контакты"),
        bullet("Описание номеров и услуг"),
        bullet("График работы (заезд/выезд)"),
        bullet("Telegram аккаунт менеджера (для уведомлений)"),
        bullet("Для WhatsApp: Meta Business аккаунт + отдельный номер телефона"),

        // ========== PAGE 2: ШПАРГАЛКА ==========
        new Paragraph({ children: [new PageBreak()] }),

        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "Шпаргалка — ответы на вопросы", size: 44, bold: true, color: BLUE })]
        }),

        // --- БАЗОВЫЕ ВОПРОСЫ ---
        heading("Стандартные вопросы", HeadingLevel.HEADING_2),

        ...qaBlock(
          "«А если мы ведём учёт в Excel?»",
          "На первом этапе бот направляет запросы на бронь менеджеру. Дальше можем сделать удобную панель прямо в системе бота — менеджер отмечает занятость, бот сам отвечает гостю. Это удобнее Excel и всё в одном месте."
        ),
        ...qaBlock(
          "«У нас Google Календарь»",
          "Отлично, Google Календарь имеет открытый API — подключим бота к нему. Бот будет видеть свободные даты и отвечать гостю сам. Вам ничего менять не нужно — продолжаете вести календарь как обычно."
        ),
        ...qaBlock(
          "«Мы на Booking / Airbnb»",
          "Они отдают календарь занятости — бот может подтягивать эти данные и понимать, какие даты заняты. Бронировать через бота напрямую на Booking не получится, но бот проверит наличие и передаст заявку менеджеру."
        ),
        ...qaBlock(
          "«У нас 1С / Opera / своя CRM»",
          "Если у системы есть API — подключимся. Нужно будет уточнить у вашего IT-специалиста доступы. Это чуть больше времени на настройку, но потом бот работает полностью автономно."
        ),
        ...qaBlock(
          "«Мы всё в тетрадке ведём»",
          "Тогда сразу сделаем удобную систему — менеджер отмечает в панели кто заехал и выехал, а бот автоматически отвечает гостям по наличию. Заодно уйдёте от тетрадки — всё будет в цифре."
        ),
        ...qaBlock(
          "«Можно без WhatsApp, только Telegram?»",
          "Конечно. Telegram подключается моментально. WhatsApp можно добавить позже в любой момент — функционал уже встроен."
        ),
        ...qaBlock(
          "«Можно посмотреть демо?»",
          "Да, могу показать бота в действии прямо в Telegram — напишите ему и посмотрите как он отвечает."
        ),

        // ========== PAGE 3: ДОТОШНЫЕ ВОПРОСЫ ==========
        new Paragraph({ children: [new PageBreak()] }),

        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "Каверзные и дотошные вопросы", size: 44, bold: true, color: "CC0000" })]
        }),

        text("Если клиент копает глубоко — вот готовые ответы:", { italics: true, color: GRAY }),

        // --- ТЕХНИЧЕСКИЕ ---
        heading("Техническая часть", HeadingLevel.HEADING_2),

        ...qaBlockRed(
          "«А если бот ответит неправильно? Кто несёт ответственность?»",
          "Бот никогда не выдумывает информацию. Он отвечает строго по базе знаний, которую вы сами наполняете. Если он не уверен — моментально подключает менеджера. Цены, наличие номеров — всегда через живого человека. Вы полностью контролируете, что бот говорит, через веб-панель."
        ),
        ...qaBlockRed(
          "«А если серверы упадут? Что будет с ботом?»",
          "Бот размещается на облачных серверах с автоматическим перезапуском. Если сервер перезагружается — бот восстанавливается за минуту. Все диалоги и данные хранятся в облачной базе данных с резервным копированием. Потерь данных не будет."
        ),
        ...qaBlockRed(
          "«На каком AI работает? А если ChatGPT / DeepSeek закроют?»",
          "Бот использует языковую модель через API. Если один провайдер перестанет работать — мы переключаем на другую модель за пару часов. Архитектура построена так, что AI-движок заменяемый. Для вас ничего не изменится."
        ),
        ...qaBlockRed(
          "«А сколько стоит содержание бота в месяц? Какие скрытые расходы?»",
          "Ежемесячные расходы минимальные — облачный сервер и AI-запросы. Точную сумму обсудим отдельно, она зависит от объёма диалогов. Никаких скрытых платежей — вы видите ровно то, что потребляете. WhatsApp от Meta — бесплатно первые 1000 диалогов в месяц."
        ),
        ...qaBlockRed(
          "«А если мы захотим уйти? Данные наши?»",
          "Все данные — ваши. База диалогов, контакты гостей, база знаний — всё можно выгрузить в любой момент. Никакой привязки. Код проекта тоже может быть передан вам."
        ),

        // --- БИЗНЕС ---
        heading("Бизнес-вопросы", HeadingLevel.HEADING_2),

        ...qaBlockRed(
          "«А у кого-то ещё такой бот есть? Можно контакт для отзыва?»",
          "Да, подобная система уже работает у другого бизнеса в Бишкеке. Могу дать контакт или показать бота в действии — напишите ему в Telegram и проверьте сами."
        ),
        ...qaBlockRed(
          "«А чем ваш бот лучше обычного автоответчика?»",
          "Автоответчик отвечает по шаблону — одно и то же на всё. Наш бот понимает контекст: что спрашивает гость, на каком языке, какой вопрос. Он ведёт диалог как живой человек, а не выдаёт шаблонную отбивку. Плюс он учится — каждый ответ менеджера делает бота умнее."
        ),
        ...qaBlockRed(
          "«Зачем нам бот, если у нас менеджер справляется?»",
          "Менеджер не может отвечать в 3 часа ночи. Менеджер болеет, уходит в отпуск, может забыть ответить. Бот — это страховка: он закрывает рутину, а менеджер занимается сложными задачами. Плюс — ни один клиент не теряется."
        ),
        ...qaBlockRed(
          "«А если нагрузка вырастет — 100 гостей одновременно?»",
          "Бот обрабатывает запросы параллельно. Хоть 10, хоть 100 гостей одновременно — каждый получит ответ за секунды. Менеджер физически не может вести 10 чатов сразу, а бот — может."
        ),
        ...qaBlockRed(
          "«А если мы поменяем цены / услуги / номера?»",
          "Заходите в веб-панель, редактируете базу знаний — бот сразу начинает использовать новую информацию. Занимает 5 минут. Или просто скажите нам — обновим."
        ),

        // --- WHATSAPP ---
        heading("Вопросы про WhatsApp", HeadingLevel.HEADING_2),

        ...qaBlockRed(
          "«Почему нужен отдельный номер для WhatsApp?»",
          "Таковы правила Meta (владелец WhatsApp). Бизнес-бот работает через WhatsApp Business API, и номер не может одновременно использоваться в обычном WhatsApp. Нужен отдельный номер — можно купить любую SIM-карту."
        ),
        ...qaBlockRed(
          "«А Meta Business аккаунт — это сложно?»",
          "Нет, создаётся за 15-20 минут. Нужна страница в Facebook и базовая информация о бизнесе. Мы поможем с настройкой."
        ),
        ...qaBlockRed(
          "«WhatsApp платный?»",
          "Первые 1000 диалогов в месяц — бесплатно. Этого более чем достаточно для большинства отелей. Если больше — минимальная доплата за каждый диалог."
        ),

        // --- БЕЗОПАСНОСТЬ ---
        heading("Безопасность и данные", HeadingLevel.HEADING_2),

        ...qaBlockRed(
          "«А данные гостей в безопасности? GDPR?»",
          "Данные хранятся на защищённом облачном сервере. Доступ — только через авторизацию. Бот не передаёт данные третьим лицам. Если нужно — можем добавить согласие на обработку данных при первом сообщении."
        ),
        ...qaBlockRed(
          "«А кто имеет доступ к переписке гостей?»",
          "Только авторизованные менеджеры вашего отеля. У каждого свой логин и пароль. Есть роли — администратор может управлять доступами. Мы как разработчики имеем доступ только для технической поддержки."
        ),

        // УНИВЕРСАЛЬНАЯ ФРАЗА
        new Paragraph({ children: [new PageBreak()] }),
        heading("Универсальные фразы на любой случай", HeadingLevel.HEADING_1),

        new Paragraph({
          spacing: { before: 200, after: 300 },
          shading: { type: ShadingType.SOLID, color: LIGHT_BLUE, fill: LIGHT_BLUE },
          children: [new TextRun({
            text: "Если вопрос про интеграцию: «Мы подключаемся к любой системе, нужно только посмотреть технические детали. На старте бот уже работает — просто передаёт заявки менеджеру. А интеграцию с вашей системой подключим следующим шагом.»",
            italics: true, size: 24
          })]
        }),
        new Paragraph({
          spacing: { after: 300 },
          shading: { type: ShadingType.SOLID, color: LIGHT_BLUE, fill: LIGHT_BLUE },
          children: [new TextRun({
            text: "Если вопрос слишком технический: «Это я уточню у команды разработки и вернусь с точным ответом. Но на работу бота это никак не повлияет.»",
            italics: true, size: 24
          })]
        }),
        new Paragraph({
          spacing: { after: 300 },
          shading: { type: ShadingType.SOLID, color: LIGHT_BLUE, fill: LIGHT_BLUE },
          children: [new TextRun({
            text: "Если давят на гарантии: «Давайте так — запустим бота, вы тестируете неделю. Если не устроит — без вопросов.»",
            italics: true, size: 24
          })]
        }),
        new Paragraph({
          spacing: { after: 300 },
          shading: { type: ShadingType.SOLID, color: RED_BG, fill: RED_BG },
          children: [new TextRun({
            text: "ВАЖНО: Никогда не говори «не знаю». Говори «уточню и отвечу» или «давайте посмотрим вместе».",
            bold: true, size: 24
          })]
        }),
      ]
    }
  ]
});

const buffer = await Packer.toBuffer(doc);
const outputPath = "C:\\Users\\alanb\\OneDrive\\Рабочий стол\\AI_Бот_для_отеля_КП.docx";
fs.writeFileSync(outputPath, buffer);
console.log("Saved:", outputPath);
