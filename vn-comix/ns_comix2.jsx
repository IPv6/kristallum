//@include "../scripts/photoshop/libs/comixgen.jsx"
var globals = {};
initComix("d:/Downloads/comix_pages", globals);

//================ INTRO ============================
switchScene("bgs","logo2");
switchScene("bgs_mods_up",null);
switchScene("bgs_mods_down",null);
switchScene("text_shade",null);
switchScene("chars",null);
say("texts",null,null);
switchScene("text_shade","main_tbg");
//================ LINES ===============================
switchScene("bgs_mods_up","record_mode_on");
switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_down","papsh_logo");
switchScene("chars","r_ja2_smi",["texts","r"]);
say(null,null,"Доброй ночи! Вижу в чате... уже все собрались, давайте начнем.");
say(null,null,"Сегодня будет совсем короткий выпуск. Даже не выпуск, а... не знаю как назвать.");
switchScene("chars","r_ja2_sur",["texts","r"]);
say(null,null,"Я просто возмущена невежеством некоторых товарищей!");
say(null,null,"Мне вот пишут, что расследования ненастоящие, и что вся передача это...");
switchScene("bgs_mods_down","papsh_class");
say(null,null,"Это обман, чтобы набрать классы.");
switchScene("bgs_mods_down","papsh_really");
say(null,null,"Это неправда!!!");
switchScene("bgs_mods_down","papsh_class");
say(null,null,"Все расследования, которые я выкладывала - настоящие!");
switchScene("chars","r_ja2_smi2",["texts","r"]);
say(null,null,"А вот выводы...");
say(null,null,"Выводы каждый может сделать сам, конечно.");
switchScene("chars","r_ja2_smi",["texts","r"]);
switchScene("bgs_mods_down","papsh_znatok_l");
say(null,null,"А если где-то ошибка - так и скажите.");
switchScene("chars","r_ja2_sur",["texts","r"]);
say(null,null,"Только аргументировано, пожалуйста!");
switchScene("bgs_mods_down","papsh_ban");
switchScene("chars","r_ja2_sur",["texts","r"])
say(null,null,"Потому что за неконструктивную критику полагается Б.А.Н!");

switchScene("bgs_mods_down","papsh_znatok_l");
switchScene("chars","r_ja2_smi",["texts","r"]);
say(null,null,"Но я все таки решила немного поменять передачу.");
switchScene("chars","r_ja2_smi2",["texts","r"]);
say(null,null,"Поэтому, чтобы закрыть один вопрос - я пригласила в гости специалиста.");
switchScene("bgs_mods_down","papsh_znatok_l");
switchScene("chars","r_ja2_lau",["texts","r"]);
say(null,null,"И сегодня у нас в студии - настоящий ЗНАТОК.");
say(null,null,"Заместитель руководителя отдела С.О.С...");
switchScene("chars","r_ja2_smi2",["texts","r"]);
say(null,null,"Аркадий Максимович Шликенблюхер.");
say(null,null,"Встречаем, в гостях у инопланетянки!");

switchScene("bgs","nks_hall2_mrb");
switchScene("bgs_mods_down","papsh_znatok_r");
switchScene("chars","l_ge_shiken_smi",["texts","l"]);
say(null,null,"Здрайствуйте. Очень рад приглашению, очень рад.");
say(null,null,"Я смотрел предыдущие выпуски, кое-что спорно...");
say(null,null,"Но со многим можно и, я бы даже сказал, нужно согласиться.");
switchScene("chars","l_ge_shiken_hm",["texts","l"]);
say(null,null,"Только вы мою фамилию немного...");

switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_down","papsh_znatok_l");
switchScene("chars","r_ja2_smi2",["texts","r"]);
say(null,null,"Хорошо, хорошо, спасибо. Давайте перейдем к делу.");
switchScene("bgs_mods_down","papsh_whoascience_l");
say(null,null,"Как вы знаете, у нас в чате объявился знаток космонавтики, который...");
say(null,null,"... не понимает русского языка. Буквально!");
switchScene("chars","r_ja2_smi",["texts","r"]);
say(null,null,"И у нас зашел принципиальный спор о дате рождения черных дыр.");
say(null,null,"Как... как концепции.");
switchScene("chars","r_ja2_smi2",["texts","r"]);
say(null,null,"Что вы можете сказать по этому вопросу?");

switchScene("bgs","nks_hall2_mrb");
switchScene("bgs_mods_down","papsh_whoascience_r");
switchScene("chars","l_ge_shiken_smi",["texts","l"]);
say(null,null,"Да, я видел эту полемику и конечно, я могу подтвердить, что черные дыры...");
say(null,null,"Черные дыры, как концепция, появились ровно 300 лет назад.");
say(null,null,"В 1916 году. Недавно был юбилей, практически!");
say(null,null,"В 1916 году ученый по имени Карл решил уравнения ОТО и...");

switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_down","papsh_whoascience_l");
switchScene("chars","r_ja2_smi2",["texts","r"]);
say(null,null,"Вот, видите! 300 лет назад, Карл!");
switchScene("bgs","nks_hall2_mrb");
switchScene("bgs_mods_down","papsh_whoascience_r");
switchScene("chars","l_ge_shiken_smi",["texts","l"]);
say(null,null,"Да, и я хотел сказать...");
switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_down","papsh_whoascience_l");
switchScene("chars","r_ja2_smi",["texts","r"]);
say(null,null,"Спасибо, спасибо.");
say(null,null,"Достаточно, ваше мнение очень важно для нас.");

switchScene("bgs","nks_hall2_mrb");
switchScene("bgs_mods_down","papsh_whoascience_r");
switchScene("chars","l_ge_shiken_smi",["texts","l"]);
say(null,null,"... по имени Карл Шварцшильд. И, как я уже сказал, в этом году юбилей...");

switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_down","papsh_whoascience_l");
switchScene("chars","r_ja2_smi",["texts","r"]);
say(null,null,"Да, да, все как я и говорила, 300 лет назад!");
say(null,null,"А вовсе не 150 лет, как утверждали...");
say(null,null,"Некоторые так называемые 'знатоки'.");

switchScene("bgs","nks_hall2_mrb");
switchScene("bgs_mods_down","papsh_whoascience_r");
switchScene("chars","l_ge_shiken_hm",["texts","l"]);
say(null,null,"... юбилей теории относительности Энштейна...");
say(null,null,"Как известно, без черных дыр были невозможны путешествия...");

switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_down","papsh_whoascience_l");
switchScene("chars","r_ja2_smi",["texts","r"]);
say(null,null,"Да, да, хорошо.");

switchScene("bgs","nks_hall2_mrb");
switchScene("bgs_mods_down","papsh_whoascience_r");
switchScene("chars","l_ge_shiken_hm",["texts","l"]);
say(null,null,"Подождите, но я еще не все сказал...");

switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_down","papsh_whoascience_l");
switchScene("chars","r_ja2_smi",["texts","r"]);
say(null,null,"Расскажете в следующий раз.");

switchScene("bgs","nks_hall2_mrb");
switchScene("bgs_mods_down","papsh_whoascience_r");
switchScene("chars","l_ge_shiken_hm",["texts","l"]);
say(null,null,"Какой следующий раз, я всего две минутки...");

switchScene("bgs","nks_hall2_mlb");
switchScene("bgs_mods_down","papsh_whoascience_l");
switchScene("chars","r_ja2_smi",["texts","r"]);
say(null,null,"У нас уже нет времени, передача закончена, спасибо!");
switchScene("chars","r_ja2_smi2",["texts","r"]);
say(null,null,"Я рада, что вы пришли, но не забывайте, что вы в гостях.");

//================ LINES ===============================
switchScene("chars","r_ja2_lau");
switchScene("bgs_mods_down",null);
say(null,null,"Как обычно, оставляйте комментарии под этим видео.");
say(null,null,"Покеда!");
switchScene("bgs_mods_up",null);
switchScene("chars",null);
switchScene("chars",null);
switchScene("chars",null);
//====================
alert("Done!");
