//@include "../_tools/Photoshop/comixgen.jsx"
var globals = {};
initComix("d:/Downloads/comix_pages", globals);

//======================================================
switchScene("bgs","logo");
switchScene("bgs_mods",null);
switchScene("chars",null);
switchScene("bgs_mods_under",null);
switchScene("text_shade","bl_tbg");
say("texts",null,null);
//======================================================
//--- Отнестись с пониманием

switchScene("bgs","medpunkt_inner_night");
switchScene("chars","vl_right2",["texts","r"]);
say(null,null,"Что здесь происходит?");
say(null,null,"Прекратите немедленно! А ну слазьте с кушетки!");
say(null,null,"Женя, вот от тебя я такого совсем не ожидала.");
say(null,null,"И от тебя, Шурик... А такой был приличный... пионер.");

switchScene("chars","sh_right_shy2",["texts","r"]);
say(null,null,"Виолетта, извините нас. Так получилось.");

switchScene("chars","vl_right2",["texts","r"]);
say(null,null,"Ты сначала рубашку надень... пионер.");
say(null,null,"Вы другого места не могли найти?");
say(null,null,"Женя, и сними мой халат, пожалуйста.");
say(null,null,"Он все равно не твоего размера.");

switchScene("chars","zh_left_dokt_rage",["texts","l"]);
say(null,null,"Сейчас, я уже ухожу.");

switchScene("chars","sh2_right2",["texts","r"]);
say(null,null,"Женя, подожди! Ты все не так поняла!");

switchScene("chars","zh_left_dokt_rage",["texts","l"]);
say(null,null,"Все я поняла, ты меня обманул.");
say(null,null,"И не ходи за мной.");

switchScene("chars","sh2_right2",["texts","r"]);
say(null,null,"Женя! Ну подожди!");

switchScene("chars","vl_right2",["texts","r"]);
say(null,null,"Шурик, Жене надо побыть одной, тебе же ясно сказали.");
say(null,null,"Останься, кто-то же должен убрать весь этот беспорядок.");
say(null,null,"Который вы тут устроили.");

// Помехи
switchScene("bgs_mods_under","pomehi1");
say(null,null,"И раз Женя уже ушла... Расскажи что тут у вас случилось.");
switchScene("bgs_mods_under",null);

switchScene("chars","sh2_left2",["texts","l"]);
say(null,null,"Кажется я совершил ужасную глупость...");

// Помехи2
switchScene("bgs_mods_under","pomehi2");
switchScene("chars","vl_right2",["texts","r"]);
say(null,null,"Это какую же? Я надеюсь, ты не сделал Жене ничего плохого?");
switchScene("bgs_mods_under",null);

// Помехи3
switchScene("bgs_mods_under","pomehi3");
switchScene("chars","sh2_left2",["texts","l"]);
say(null,null,"Нет, просто она не так меня поняла. Я хотел как лучше...");
switchScene("chars",null);
switchScene("bgs_mods_under","pomehi2");
say("texts",null,null);
switchScene("bgs_mods_under","pomehi1");
say("texts",null,null);
switchScene("bgs_mods_under",null);

switchScene("text_shade","ks_tbg");
switchScene("chars",null);
//Кинотеатр, темно на экране скрин В+Ш2 с помехами без текста
switchScene("bgs","kinoteatr1a1");
say("texts","c2","Объявление: уважаемые зрители, возникла техническая неполадка.");
switchScene("bgs","kinoteatr1a2");
say("texts","c2","Мультифильм начнется через несколько минут. Приносим наши извинения.");
switchScene("bgs","kinoteatr1a3");
say("texts","c2","Просьба оставаться на своих местах, сеанс скоро будет продолжен.");
//Кинотеатр, на экране белое
switchScene("bgs","kinoteatr1");

switchScene("chars","ar_left_sad",["texts","l"]);
say(null,null,"Ну вот, на самом интересно месте...");
say(null,null,"Вера, ну как тебе?");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"Не зря я тебя сюда вытащил, правда?");
say(null,null,"Тебе понравилось?");

switchScene("chars","vr_right_smile",["texts","r"]);
say(null,null,"Ну да, довольно интересно.");
say(null,null,"Никогда раньше не видела старых мультифильмов.");
say(null,null,"Ты был прав, сейчас-то уже так не делают.");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"Ну вот, что я тебе говорил!");
say(null,null,"А ты за кого там смотришь?");

switchScene("chars","vr_right_norm",["texts","r"]);
say(null,null,"Я кажется за этого парня в очках... За Шурика с Электроником.");
say(null,null,"А ты?");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"А, я это видел уже. Это как он с Женей, а потом с...");

switchScene("chars","vr_right_heh",["texts","r"]);
say(null,null,"Не надо мне рассказывать, я сама хочу посмотреть!");
say(null,null,"А у тебя за кого показывают?");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"У меня показывают за Алису и Лену, очень интересно.");
say(null,null,"Это одна из последних добавок, когда он еще в широком прокате шел.");
say(null,null,"Я на сайте читал.");

switchScene("chars","vr_right_norm",["texts","r"]);
say(null,null,"Алису и... Лену? Это как это?");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"Да там чего только не придумали, времена были такие.");
say(null,null,"Сейчас так не делают!");
say(null,null,"А ты знаешь, что это один из первых мультифильмов? В широком прокате?");
say(null,null,"Их сначала по известным играм создавали.");
say(null,null,"Где было много сюжетных линий. Фанаты разные.");
say(null,null,"А представляешь, раньше люди ходили в кинотеатр и...");
say(null,null,"И смотрели один и тот же фильм! Всем залом!");

switchScene("chars","vr_right_heh",["texts","r"]);
say(null,null,"Зачем? Глупость какая.");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"Ну вот так. Приходили и смотрели одно и тоже, пока в 22ом веке...");

//Кинотеатр, темно на экране лес
switchScene("bgs","kinoteatr1a4");
switchScene("chars","vr_right_smile",["texts","r"]);
say(null,null,"Кажется началось.");
switchScene("chars","vr_right_norm",["texts","r"]);
say(null,null,"Артем, потом расскажешь. Давай досмотрим.");

// Лес вечер, Ж+Ш2
switchScene("bgs","les_polanka");
switchScene("text_shade","bl_tbg");
switchScene("chars","zh_left_norm",["texts","l"]);
say(null,null,"Саша, отстань от меня.");
say(null,null,"Не хочу тебя видеть больше.");

switchScene("chars","sh2_right",["texts","r"]);
say(null,null,"Женя, ну я же извинился.");
say(null,null,"Глупо все как-то вышло. Давай забудем, что было.");

switchScene("chars","zh_left_norm",["texts","l"]);
say(null,null,"Я так не могу. И вообще, все слишком быстро случилось.");
say(null,null,"Мне надо разобраться... В себе.");
say(null,null,"Поэтому оставь меня в покое. Пожалуйста.");

switchScene("chars","sh2_right",["texts","r"]);
say(null,null,"Понятно. Знаешь, что я хочу тебе сказать...");
say(null,null,"Если у нас получится отсюда выбраться...");
say(null,null,"Если получится...");
say(null,null,"Я не знаю где ты проснешся после лагеря.");
say(null,null,"Но... Приходи на красную площадь. Я будут тебя ждать.");
say(null,null,"Каждый день, в шесть вечера. С цветами...");
say(null,null,"Приходи. Я буду ждать.");

switchScene("chars","el_left",["texts","l"]);
say(null,null,"Шурик, кого это ты будешь ждать на Красной площади?");
say(null,null,"Да еще с цветами? Меня что ли?");

// Помехи
switchScene("bgs_mods_under","pomehi4");
switchScene("chars","sh2_right",["texts","r"]);
say(null,null,"Электроник, не до шуток сейчас.");
switchScene("bgs_mods_under",null);

switchScene("chars","zh_left_norm",["texts","l"]);
say(null,null,"Электроник, вот только тебя тут не хватало, для полного комплекта.");

switchScene("bgs_mods_under","pomehi5");
say(null,null,"И так тошно, иди к остальным. Тебя это не касается.");
switchScene("bgs_mods_under",null);

switchScene("bgs_mods_under","pomehi4");
switchScene("chars","el_left",["texts","l"]);
say(null,null,"Что-то вы опять не в духе. Ну ладно, и пойду.");
switchScene("bgs_mods_under","pomehi6");
switchScene("chars",null);
say("texts",null,null);
switchScene("bgs_mods_under",null);

//Кинотеатр, светло на экране белое
switchScene("bgs","kinoteatr1");
switchScene("chars",null);
switchScene("text_shade","ks_tbg");
say("texts","c2","Объявление: уважаемые зрители, у нас снова возникла техническая неполадка");
say("texts","c2","Просьба оставаться на своих местах, сеанс скоро будет продолжен.");

switchScene("chars","ar_left_sad",["texts","l"]);
say(null,null,"Да что же это такое!");
say(null,null,"Наверное оборудование старое, никто не следил за ним...");
say(null,null,"Cейчас это уже не модно...");

switchScene("chars","vr_right_norm",["texts","r"]);
say(null,null,"Ну может быть, может быть. А что там у тебя происходит?");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"У меня... Там же они у тебя в походе сейчас, так?");

switchScene("chars","vr_right_norm",["texts","r"]);
say(null,null,"Ага. У меня вот Женя с Шуриком опять ругаются... Надеюсь помирятся, все таки.");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"Ага, помирятся... увидишь. А у меня в это время...");
say(null,null,"Лена с Алисой от всех сбежали.");
say(null,null,"И заблудились в лесу. И сейчас их Юля ведет в одно место...");

switchScene("chars","vr_right_heh",["texts","r"]);
say(null,null,"Юля? Кто такая Юля?");

switchScene("chars","ar_left_smile",["texts","l"]);
say(null,null,"Ну ты ее не знаешь еще.");
say(null,null,"Она потом появляется. У тех, кто уже видел основные части этой истории.");

switchScene("chars","vr_right_heh",["texts","r"]);
say(null,null,"Понятно.");

//Кинотеатр, темно на экране ОД прощается.
switchScene("bgs","kinoteatr1a5");
switchScene("chars","vr_right_smile",["texts","r"]);
say(null,null,"Ой, снова началось.");

// ОД прощается
switchScene("chars",null);
switchScene("text_shade","bl_tbg");
switchScene("bgs","od_dosvodos");
say("texts","c2","Сегодня вы покидаете наш лагерь, и на прощание мне хотелось бы вам кое-что сказать.");
say("texts","c2","Надеюсь, что время, проведённое здесь, вам запомнится на всю жизнь.");
say("texts","c2","В общем, возвращайтесь в следующем году!");

// Икарус
switchScene("bgs","ikarus");
switchScene("chars","sh2_right",["texts","r"]);
say(null,null,"Женя, можно сесть рядом с тобой? В автобусе?");

switchScene("chars","zh_left_norm",["texts","l"]);
say(null,null,"Нет, нельзя, иди к своему Электронику.");

switchScene("chars","sh2_right",["texts","r"]);
say(null,null,"Понятно... Я все равно буду тебя ждать.");

switchScene("chars","el_left",["texts","l"]);
say(null,null,"На красной площади? С цветами? В шесть часов?");
say(null,null,"Женя, ты учти, я тоже приду!");
say(null,null,"И цветов... у меня будет больше!");

switchScene("chars","zh_left_norm",["texts","l"]);
say(null,null,"Ага, вот только тебя там и не хватало.");
say(null,null,"Хотя... вы сможете там этими цветами торговать.");
say(null,null,"Хоть какая-то от вас польза будет.");
say(null,null,"Садитесь в автобус, нас уже ждут.");

// В автобусе
switchScene("chars",null);
switchScene("bgs","ikarus_inside");
say("texts","c2","Вот так и закончилась эта история...");
switchScene("bgs","zakat");
switchScene("bgs_mods","achivka");// + ачивемент анлокед: побег из курятника
say("texts","c","Еще одна смена в Бесконечном Лете.");

// Красная площадь наши дни
switchScene("bgs","resquare");
switchScene("chars","sh_right_cvt",["texts","r"]);
say(null,null,"Не подскажете сколько времени?");
switchScene("bgs_mods",null);

// Сбоку бабл
switchScene("bgs_mods","buble_text");
say("texts","l","Полвосьмого.");
switchScene("bgs_mods",null);

switchScene("chars","sh_right_cvt",["texts","r"]);
say(null,null,"Спасибо.");
say(null,null,"Ладно. Пойду прогуляюсь.");

switchScene("chars","zh_left_smile",["texts","l"]);
say(null,null,"Меня подожди.");

switchScene("chars","sh_right_smile_cvt",["texts","r"]);
say(null,null,"Женя!!!");

switchScene("chars","el_left",["texts","l"]);
say(null,null,"И меня, меня тоже подождите!");

switchScene("chars","zh_left_norm2",["texts","l"]);
say(null,null,"Электроник???");

switchScene("chars","sh_right_scared1",["texts","r"]);
say(null,null,"А ты как сюда попал???");
say("texts", null, null);

// Красная площадь+Конец
switchScene("chars",null);
say("texts", "c", "КОНЕЦ");

switchScene("bgs","black");
say("texts", "c", "КОНЕЦ");
switchScene("text_shade",null);

// Вечер, силуэты Толика+Памеллы
switchScene("bgs","finaltitrs1");

// В главных ролях: --- - -- --- 
switchScene("bgs_mods","titrs1");
say("texts",null, null);

// Художники по костюмам: --- - -- 
switchScene("bgs_mods","titrs2");
say("texts",null, null);

// Снято по заказу гостелерадио России в 2056 году
// Разрешено к показу на всех внеземных колониях золотого кольца.
switchScene("bgs_mods","titrs3");
say("texts",null, null);

// Спасибо за просмотр
//                 (с)2215 Станция Омега, http://vk.com/krajsveta
switchScene("bgs_mods","titrs4");
say("texts",null, null);
say("texts",null, null);
say("texts",null, null);

//====================
alert("Done! pages=" + globals.pageIndex);