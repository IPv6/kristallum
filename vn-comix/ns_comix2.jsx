//@include "../scripts/photoshop/libs/comixgen.jsx"
var globals = {};
initComix("d:/Downloads/comix_pages", globals);

//================ INTRO ============================
switchScene("bgs","logo");
switchScene("bgs_mods_up",null);
switchScene("bgs_mods_down",null);
switchScene("text_shade",null);
switchScene("chars",null);
say("texts",null,null);
switchScene("text_shade","main_tbg");
//================ LINES ===============================
switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_up","record_mode_on");
switchScene("bgs_mods_down","papsh_logo");
switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Доброй ночи! Вижу в чате... уже все собрались, давайте начнем.");
say(null,null,"Сегодня будет совсем короткий выпуск. Даже не выпуск, а... не знаю как назвать.");
say(null,null,"Я просто возмущена невежеством некоторых товарищей!");
say(null,null,"Мне вот пишут, что расследования ненастоящие, и что все это придумано...");
say(null,null,"Это все обман, чтобы набрать классы!");
say(null,null,"Это неправда!");
say(null,null,"Все расследования, которые я выкладывала - настоящие! А вот выводы...");
say(null,null,"Выводы каждый может сделать сам, конечно.");
say(null,null,"Или хотя бы указать мне на неточности. Снова повторю:");
say(null,null,"За неконструктивную критику полагается Б.А.Н! БАН!");
switchScene("bgs_mods_down",null);
say(null,null,"Но я все таки решила немного поменять формат моей передачи.");
say(null,null,"И сегодня, чтобы окончательно закрыть один вопрос...");
say(null,null,"Я пригласила к нам в студию настоящего Знатока.");
say(null,null,"Заместителя руководителя отдела С.О.С...");
say(null,null,"Аркадия Максимовича Шликенблюхера. Встречаем!");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Здрайствуйте. Очень рад приглашению, очень рад.");
say(null,null,"Я смотрел предыдущие выпуски, кое-что спорно, но со многим можно и нужно согласиться.");
say(null,null,"Только вы мою фамилию немного...");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Хорошо, хорошо, спасибо. Давайте перейдем к делу.");
say(null,null,"Как вы знаете, у нас в чате объявился знаток космонавтики и истории.");
say(null,null,"Который буквально не понимает русского языка.");
say(null,null,"И у нас зашел принципиальный спор о дате рождения черных дыр.");
say(null,null,"Как... как концепции.");
say(null,null,"Что вы можете сказать по этому вопросу?");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Да, я видел эту ветку и конечно, я могу подтвердить, что черные дыры...");
say(null,null,"Черные дыры, как концепция, появились ровно 300 лет назад.");
say(null,null,"В 1916 году. Юбилей, практически!");
say(null,null,"300 лет назад ученый, по имени Карл Шварцшильд, решил уравнения ОТО и...");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Вот! Видите! Спасибо, спасибо.");
say(null,null,"Достаточно, ваше мнение очень важно для всех.");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Да. И, как я уже сказал, в этом году юбилей теории относительности Эншт...");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Да, да, все как я и говорила, 300 лет назад!");
say(null,null,"А вовсе не 150 лет, как утверждали некоторые.");
say(null,null,"Некоторые так называемые 'знатоки'.");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Да. Как известно, без черных дыр были бы невозможны путешествия между звездами...");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Да, да, хорошо.");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Подождите, но я еще не все сказал...");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Расскажете в следующий раз.");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Какой следующий раз, я всего две минутки...");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"У нас уже нет времени, все, передача закончена, спасибо!");
say(null,null,"Спасибо что пришли, давайте закруглимся.");
//================ LINES ===============================
say(null,null,"Как обычно, оставляйте комментарии под этим видео.");
switchScene("chars","r_ja_lau_spok");
say(null,null,"Спокеда!");
switchScene("bgs_mods_up",null);
switchScene("chars",null);
switchScene("chars",null);
switchScene("chars",null);
//====================
alert("Done!");
