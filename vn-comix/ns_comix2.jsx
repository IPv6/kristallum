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
say(null,null,"Доброй ночи! Вижу в чате уже все собрались, начнем.");
say(null,null,"Мне вот часто пишут, что расследования ненастоящие, и что...");
say(null,null,"Это все обман, чтобы набрать классы!");
say(null,null,"Что все заранее придумано, и на самом деле совсем не так.");
say(null,null,"Это неправда!");
say(null,null,"Все расследования, которые я выкладывала - настоящие, а выводы...");
say(null,null,"Выводы каждый может сделать сам. Или хотя бы указать на неточности!");
say(null,null,"Помните: За неконструктивную критику полагается Б.А.Н.");
switchScene("bgs_mods_down",null);
say(null,null,"Но я все таки решила немного поменять формат, и в этот раз...");
say(null,null,"У нас будет пробный выпуск. Я на него пригласила настоящего знатока...");
say(null,null,"Заместителя руководителя Секретного Отдела С**...");
say(null,null,"Аркадий Максимович Шикенблюхер. Встречаем!");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Здрайствуйте. Очень рад приглашению, очень рад.");
say(null,null,"Я смотрел предыдущие выпуски, кое-что спорно, но со многим можно согласиться.");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Хорошо, хорошо, давайте перейдем к делу.");
say(null,null,"Как вы знаете, у нас в чате объявился космобиолог.");
say(null,null,"И зашел спор о дате рождения черных дыр, как концепции.");
say(null,null,"Что вы можете сказать по этому вопросу?");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Да, я видел этот пост и конечно, я могу подтвердить, что...");
say(null,null,"Черные дыры как концепция появились ровно 300 лет назад.");
say(null,null,"Ученый, по имени Карл Шварцшильд, решил в 1916 уравнения ОТО и...");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Вот! Видите! Спасибо, спасибо, ваше мнение очень важно для всех.");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Да. И, кстати, в этом году практически юбилей всей теории относительности...");

switchScene("chars","r_ja_smi",["texts","r"]);
say(null,null,"Да, да, все как я и говорила, 300 лет назад!");
say(null,null,"А вовсе не 150 лет, как утверждали мне некоторые.");
say(null,null,"Так называемые 'знатоки'.");

switchScene("chars","r_ge_shiken",["texts","l"]);
say(null,null,"Как известно, без черных дыр невозможны быстрые путешествия между звездами...");

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
