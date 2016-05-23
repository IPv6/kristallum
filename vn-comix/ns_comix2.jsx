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

"ВГостях" представляет обзор ретро-фильма
вышел двести лет назад!
одна версия для всех
смотрим сюжет

//================ LINES ===============================
say(null,null,"Пишите свои комментарии и предложения на следующий раз.");
say(null,null,"Как обычно, под этим видео.");
switchScene("chars","r_ja_lau_spok");
say(null,null,"Спокеда!");
switchScene("chars",null);
//======================================================
//switchScene("bgs_mods_up","menu");
//say("texts",null, null);
//====================
alert("Done!");
