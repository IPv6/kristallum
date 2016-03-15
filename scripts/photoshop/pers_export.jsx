//@include "libs/comixgen.jsx"
//@include "libs/persutils.jsx"

//var exportTo = "tamojk";
//var exportTo = "prof";
//var exportTo = "sasha";
//var exportTo = "gena";
//var exportTo = "artem";
//var exportTo = "anton";
//var exportTo = "ura";
//var exportTo = "janna";

//var exportTo = "belpoli";
var exportTo = "samanta";
//var exportTo = "anna";
//var exportTo = "katya";
//var exportTo = "vera";
//var exportTo = "kasatka";
//var exportTo = "marina";


var globals = {};
initComix("d:/Downloads/"+exportTo, globals);

//======================================================
var duppedDocument = null;
var json_cnt = "";
switchScene(null, null);
var scaleFactor = 0.58; //0.71145833333 - 2048 problem;// 1920->1366
var refs_path = "/vn_storyline/art/pers2/";

if(exportTo == "tamojk"){

	var bodies = [
		["tamojk_p1_dress1","posa1","body+dress"],
		["tamojk_p2_dress1","posa2","body+dress"],
	];

	// Emotions tamojk
	var emots = [
		["tamojk_p1_nrm","posa1","nrm"],
		["tamojk_p1_smi","posa1","smi"],
		["tamojk_p1_lau","posa1","lau"],
		["tamojk_p1_sur","posa1","sur"],
		["tamojk_p1_hm","posa1","hm"],
		
		["tamojk_p2_nrm","posa2","nrm"],
		["tamojk_p2_smi","posa2","smi"],
		["tamojk_p2_lau","posa2","lau"],
		["tamojk_p2_sur","posa2","sur"],
		["tamojk_p2_hm","posa2","hm"]
	];

	// Avatar tamojk
	var avats = [
		["_tamojk_nrm","posa1","body+nrm"],
		["_tamojk_smi","posa1","body+smi"],
		["_tamojk_lau","posa1","body+lau"],
		["_tamojk_sur","posa1","body+sur"],
		["_tamojk_hm","posa1","body+hm"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "prof"){

	var bodies = [
		["prof_p1_dress1","posa1","body+dress+hairs"]
	];

	// Emotions prof
	var emots = [
		["prof_p1_nrm","posa1","nrm+hairs"],
		["prof_p1_hm","posa1","hm+hairs"],
		["prof_p1_smi","posa1","smi+hairs"],
		["prof_p1_lau","posa1","lau+hairs"],
		["prof_p1_sur","posa1","sur+hairs"]
	];

	// Avatar prof
	var avats = [
		["_prof_nrm","posa1","body+nrm+hairs"],
		["_prof_hm","posa1","body+hm+hairs"],
		["_prof_smi","posa1","body+smi+hairs"],
		["_prof_lau","posa1","body+lau+hairs"],
		["_prof_sur","posa1","body+sur+hairs"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "sasha"){

	var bodies = [
		["sasha_p1_dress1","posa1","body+dress1+hairs1+hairs2"],
		["sasha_p1_dress2","posa1","body+dress2+hairs1+hairs2"],
		["sasha_p2_dress1","posa2","body+dress1+hairs1+hairs2"],
		["sasha_p2_dress2","posa2","body+dress2+hairs1+hairs2"]
	];

	// Emotions sasha
	var emots = [
		["sasha_p1_nrm","posa1","nrm"],
		["sasha_p1_smi","posa1","smi"],
		["sasha_p1_lau","posa1","lau"],
		["sasha_p1_hm","posa1","hm"],
		["sasha_p1_sur","posa1","sur"],
		
		["sasha_p2_nrm","posa2","nrm"],
		["sasha_p2_smi","posa2","smi"],
		["sasha_p2_lau","posa2","lau"],
		["sasha_p2_hm","posa2","hm"],
		["sasha_p2_sur","posa2","sur"]
	];

	// Avatar sasha
	var avats = [
		["_sasha_nrm","posa1","hairs1+body+nrm+hairs2"],
		["_sasha_hm","posa1","hairs1+body+hm+hairs2"],
		["_sasha_smi","posa1","hairs1+body+smi+hairs2"],
		["_sasha_lau","posa1","hairs1+body+lau+hairs2"],
		["_sasha_sur","posa1","hairs1+body+sur+hairs2"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "belpoli"){

	var bodies = [
		["bpl_p1_dress1","posa1","body+dress1+hairs2+hairs2_shadow"],
		["bpl_p1_dress2","posa1","body+dress2+hairs2+hairs2_shadow"],
		["bpl_p2_dress1","posa2","body+dress1+hairs2+hairs2_shadow"],
		["bpl_p2_dress2","posa2","body+dress2+hairs2+hairs2_shadow"],
	];

	var emots = [
		["bpl_p1_nrm","posa1","nrm"],
		["bpl_p1_smi","posa1","smi"],
		["bpl_p1_lau","posa1","lau"],
		["bpl_p1_sur","posa1","sur"],
		["bpl_p1_hm","posa1","hm"],
		
		["bpl_p2_nrm","posa2","nrm"],
		["bpl_p2_smi","posa2","smi"],
		["bpl_p2_lau","posa2","lau"],
		["bpl_p2_sur","posa2","sur"],
		["bpl_p2_hm","posa2","hm"]
	];

	var avats = [
		["_bpl_nrm","posa1","body+hairs2+hairs2_shadow+nrm"],
		["_bpl_hm","posa1","body+hairs2+hairs2_shadow+hm"],
		["_bpl_smi","posa1","body+hairs2+hairs2_shadow+smi"],
		["_bpl_lau","posa1","body+hairs2+hairs2_shadow+lau"],
		["_bpl_sur","posa1","body+hairs2+hairs2_shadow+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "samanta"){

	var bodies = [
		["samanta_p1_dress1","posa1","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["samanta_p1_dress2","posa1","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["samanta_p2_dress1","posa2","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["samanta_p2_dress2","posa2","hairs1+body+dress2+hairs2+hairs2_shadow"],
	];

	var emots = [
		["samanta_p1_nrm","posa1","nrm"],
		["samanta_p1_smi","posa1","smi"],
		["samanta_p1_lau","posa1","lau"],
		["samanta_p1_sur","posa1","sur"],
		["samanta_p1_hm","posa1","hm"],
		
		["samanta_p2_nrm","posa2","nrm"],
		["samanta_p2_smi","posa2","smi"],
		["samanta_p2_lau","posa2","lau"],
		["samanta_p2_sur","posa2","sur"],
		["samanta_p2_hm","posa2","hm"]
	];

	var avats = [
		["_samanta_nrm","posa1","hairs1+body+hairs2+hairs2_shadow+nrm"],
		["_samanta_hm","posa1","hairs1+body+hairs2+hairs2_shadow+hm"],
		["_samanta_smi","posa1","hairs1+body+hairs2+hairs2_shadow+smi"],
		["_samanta_lau","posa1","hairs1+body+hairs2+hairs2_shadow+lau"],
		["_samanta_sur","posa1","hairs1+body+hairs2+hairs2_shadow+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "anna"){

	var bodies = [
		["anna_p1_dress1","posa1","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["anna_p1_dress2","posa1","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["anna_p2_dress1","posa2","hairs1+body+dress1+hairs2+hairs2_shadow+body_part2"],
		["anna_p2_dress2","posa2","hairs1+body+dress2+hairs2+hairs2_shadow+body_part2"],
	];

	var emots = [
		["anna_p1_nrm","posa1","nrm"],
		["anna_p1_smi","posa1","smi"],
		["anna_p1_lau","posa1","lau"],
		["anna_p1_sur","posa1","sur"],
		["anna_p1_hm","posa1","hm"],
		
		["anna_p2_nrm","posa2","nrm"],
		["anna_p2_smi","posa2","smi"],
		["anna_p2_lau","posa2","lau"],
		["anna_p2_sur","posa2","sur"],
		["anna_p2_hm","posa2","hm"]
	];

	var avats = [
		["_anna_nrm","posa1","hairs1+body+hairs2+hairs2_shadow+nrm"],
		["_anna_hm","posa1","hairs1+body+hairs2+hairs2_shadow+hm"],
		["_anna_smi","posa1","hairs1+body+hairs2+hairs2_shadow+smi"],
		["_anna_lau","posa1","hairs1+body+hairs2+hairs2_shadow+lau"],
		["_anna_sur","posa1","hairs1+body+hairs2+hairs2_shadow+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "katya"){

	var bodies = [
		["katya_p1_dress1","posa1","hairs1+body+dress1+hairs2+hairs3"],
		["katya_p2_dress1","posa2","hairs1+body+dress1+hairs2+hairs3"]
	];

	var emots = [
		["katya_p1_nrm","posa1","nrm"],
		["katya_p1_smi","posa1","smi"],
		["katya_p1_lau","posa1","lau"],
		["katya_p1_sur","posa1","sur"],
		["katya_p1_hm","posa1","hm"],
		
		["katya_p2_nrm","posa2","nrm"],
		["katya_p2_smi","posa2","smi"],
		["katya_p2_lau","posa2","lau"],
		["katya_p2_sur","posa2","sur"],
		["katya_p2_hm","posa2","hm"]
	];

	var avats = [
		["_katya_nrm","posa1","hairs1+body+hairs2+hairs3+nrm"],
		["_katya_hm","posa1","hairs1+body+hairs2+hairs3+hm"],
		["_katya_smi","posa1","hairs1+body+hairs2+hairs3+smi"],
		["_katya_lau","posa1","hairs1+body+hairs2+hairs3+lau"],
		["_katya_sur","posa1","hairs1+body+hairs2+hairs3+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "vera"){

	var bodies = [
		["vera_p1_dress1","posa1","body+dress1+hairs2+hairs2_shadow+hairs3_dress1"],
		["vera_p1_dress2","posa1","body+dress2+hairs2+hairs2_shadow+hairs3_dress2"],
		["vera_p2_dress1","posa2","body+dress1+hairs2+hairs2_shadow+hairs3_dress1+body_part2"],
		["vera_p2_dress2","posa2","body+dress2+hairs2+hairs2_shadow+hairs3_dress2+body_part2"],
	];

	var emots = [
		["vera_p1_nrm","posa1","nrm"],
		["vera_p1_smi","posa1","smi"],
		["vera_p1_lau","posa1","lau"],
		["vera_p1_sur","posa1","sur"],
		["vera_p1_hm","posa1","hm"],
		["vera_p1_rage","posa1","rage"],
		
		["vera_p2_nrm","posa2","nrm"],
		["vera_p2_smi","posa2","smi"],
		["vera_p2_lau","posa2","lau"],
		["vera_p2_sur","posa2","sur"],
		["vera_p2_rage","posa2","rage"],
		["vera_p2_hm","posa2","hm"]
	];

	var avats = [
		["_vera_nrm","posa1","body+hairs2+hairs2_shadow+nrm"],
		["_vera_smi","posa1","body+hairs2+hairs2_shadow+smi"],
		["_vera_lau","posa1","body+hairs2+hairs2_shadow+lau"],
		["_vera_sur","posa1","body+hairs2+hairs2_shadow+sur"],
		["_vera_hm","posa1","body+hairs2+hairs2_shadow+hm"],
		["_vera_rage","posa1","body+hairs2+hairs2_shadow+rage"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "kasatka"){

	var bodies = [
		["kasatka_p1_dress1","posa1","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["kasatka_p1_dress2","posa1","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["kasatka_p2_dress1","posa2","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["kasatka_p2_dress2","posa2","hairs1+body+dress2+hairs2+hairs2_shadow"],
	];

	var emots = [
		["kasatka_p1_nrm","posa1","nrm"],
		["kasatka_p1_smi","posa1","smi"],
		["kasatka_p1_lau","posa1","lau"],
		["kasatka_p1_sur","posa1","sur"],
		["kasatka_p1_hm","posa1","hm"],
		
		["kasatka_p2_nrm","posa2","nrm"],
		["kasatka_p2_smi","posa2","smi"],
		["kasatka_p2_lau","posa2","lau"],
		["kasatka_p2_sur","posa2","sur"],
		["kasatka_p2_hm","posa2","hm"]
	];

	var avats = [
		["_kasatka_nrm","posa1","hairs1+body+hairs2+hairs2_shadow+nrm"],
		["_kasatka_hm","posa1","hairs1+body+hairs2+hairs2_shadow+hm"],
		["_kasatka_smi","posa1","hairs1+body+hairs2+hairs2_shadow+smi"],
		["_kasatka_lau","posa1","hairs1+body+hairs2+hairs2_shadow+lau"],
		["_kasatka_sur","posa1","hairs1+body+hairs2+hairs2_shadow+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "marina"){

	var bodies = [
		["marina_p1_dress1a","posa1","hairs1a+body+dress1+hairs2+hairs2_shadow+hairs3a+hairs4a"],
		["marina_p1_dress2a","posa1","hairs1a+body+dress2+hairs2+hairs2_shadow+hairs3a+hairs4a"],
		["marina_p2_dress1a","posa2","hairs1a+body+dress1+hairs2+hairs2_shadow+hairs3a+hairs4a"],
		["marina_p2_dress2a","posa2","hairs1a+body+dress2+hairs2+hairs2_shadow+hairs3a+hairs4a"],
		
		["marina_p1_dress1b","posa1","hairs1b+body+dress1+hairs2+hairs2_shadow"],
		["marina_p1_dress2b","posa1","hairs1b+body+dress2+hairs2+hairs2_shadow"],
		["marina_p2_dress1b","posa2","hairs1b+body+dress1+hairs2+hairs2_shadow"],
		["marina_p2_dress2b","posa2","hairs1b+body+dress2+hairs2+hairs2_shadow"]
	];

	var emots = [
		["marina_p1_nrm","posa1","nrm"],
		["marina_p1_smi","posa1","smi"],
		["marina_p1_lau","posa1","lau"],
		["marina_p1_sur","posa1","sur"],
		["marina_p1_hm","posa1","hm"],
		
		["marina_p2_nrm","posa2","nrm"],
		["marina_p2_smi","posa2","smi"],
		["marina_p2_lau","posa2","lau"],
		["marina_p2_sur","posa2","sur"],
		["marina_p2_hm","posa2","hm"]
	];

	var avats = [
		["_marina_nrm","posa1","hairs1a+body+hairs2+hairs3a+hairs4a+nrm"],
		["_marina_hm","posa1","hairs1a+body+hairs2+hairs3a+hairs4a+hm"],
		["_marina_smi","posa1","hairs1a+body+hairs2+hairs3a+hairs4a+smi"],
		["_marina_lau","posa1","hairs1a+body+hairs2+hairs3a+hairs4a+lau"],
		["_marina_sur","posa1","hairs1a+body+hairs2+hairs3a+hairs4a+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "gena"){

	var bodies = [
		["gena_p1_dress1","posa1","body+dress1+hairs2+hairs2_shadow"],
		["gena_p1_dress2","posa1","body+dress2+hairs2+hairs2_shadow"]
	];

	var emots = [
		["gena_p1_nrm","posa1","nrm"],
		["gena_p1_smi","posa1","smi"],
		["gena_p1_lau","posa1","lau"],
		["gena_p1_sur","posa1","sur"],
		["gena_p1_hm","posa1","hm"]
	];

	var avats = [
		["_gena_nrm","posa1","body+hairs2+nrm"],
		["_gena_hm","posa1","body+hairs2+hm"],
		["_gena_smi","posa1","body+hairs2+smi"],
		["_gena_lau","posa1","body+hairs2+lau"],
		["_gena_sur","posa1","body+hairs2+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "artem"){

	var bodies = [
		["artem_p1_dress1","posa1","body+dress1"],
		["artem_p1_dress2","posa1","body+dress2"],
		["artem_p2_dress1","posa2","body+dress1"],
		["artem_p2_dress2","posa2","body+dress2"],
		["artem_p3_dress1","posa3","body+dress1"],
		["artem_p3_dress2","posa3","body+dress2"]
	];

	var emots = [
		["artem_p1_nrm","posa1","nrm"],
		["artem_p1_smi","posa1","smi"],
		["artem_p1_lau","posa1","lau"],
		["artem_p1_sur","posa1","sur"],
		["artem_p1_hm","posa1","hm"],
		["artem_p1_cry","posa1","cry"],
		
		["artem_p2_nrm","posa2","nrm"],
		["artem_p2_smi","posa2","smi"],
		["artem_p2_lau","posa2","lau"],
		["artem_p2_sur","posa2","sur"],
		["artem_p2_hm","posa2","hm"],
		["artem_p2_cry","posa2","cry"],
		
		["artem_p3_nrm","posa3","nrm"],
		["artem_p3_smi","posa3","smi"],
		["artem_p3_lau","posa3","lau"],
		["artem_p3_sur","posa3","sur"],
		["artem_p3_hm","posa3","hm"],
		["artem_p3_cry","posa3","cry"],
	];

	var avats = [
		["_artem_nrm","posa1","body+nrm"],
		["_artem_hm","posa1","body+hm"],
		["_artem_cry","posa1","body+cry"],
		["_artem_smi","posa1","body+smi"],
		["_artem_lau","posa1","body+lau"],
		["_artem_sur","posa1","body+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "anton"){

	var bodies = [
		["anton_p1_dress1","posa1","body+dress1"],
		["anton_p1_dress2","posa1","body+dress2"]
	];

	var emots = [
		["anton_p1_nrm","posa1","nrm"],
		["anton_p1_smi","posa1","smi"],
		["anton_p1_lau","posa1","lau"],
		["anton_p1_sur","posa1","sur"],
		["anton_p1_hm","posa1","hm"]
	];

	var avats = [
		["_anton_nrm","posa1","body+nrm"],
		["_anton_hm","posa1","body+hm"],
		["_anton_smi","posa1","body+smi"],
		["_anton_lau","posa1","body+lau"],
		["_anton_sur","posa1","body+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "ura"){

	var bodies = [
		["ura_p1_dress1","posa1","body+dress1+dress1_hat"],
		["ura_p1_dress2","posa1","body+dress2"],
		
		["ura_p2_dress1","posa2","body+dress1+dress1_hat"],
		["ura_p2_dress2","posa2","body+dress2"]
	];

	var emots = [
		["ura_p1_nrm","posa1","nrm"],
		["ura_p1_smi","posa1","smi"],
		["ura_p1_lau","posa1","lau"],
		["ura_p1_sur","posa1","sur"],
		["ura_p1_hm","posa1","hm"],
		
		["ura_p2_nrm","posa2","nrm"],
		["ura_p2_smi","posa2","smi"],
		["ura_p2_lau","posa2","lau"],
		["ura_p2_sur","posa2","sur"],
		["ura_p2_hm","posa2","hm"]
	];

	var avats = [
		["_ura_nrm","posa1","body+nrm"],
		["_ura_hm","posa1","body+hm"],
		["_ura_smi","posa1","body+smi"],
		["_ura_lau","posa1","body+lau"],
		["_ura_sur","posa1","body+sur"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}


if(exportTo == "janna"){

	var bodies = [
		["janna_p1_dress1","posa1","body+dress1+hairs2+hairs2_shadow"],
		["janna_p2_dress1","posa2","body+dress1+hairs2+hairs2_shadow"]
	];

	var emots = [
		["janna_p1_nrm","posa1","nrm+glasses"],
		["janna_p1_smi","posa1","smi+glasses"],
		["janna_p1_lau","posa1","lau+glasses"],
		["janna_p1_sur","posa1","sur+glasses"],
		["janna_p1_hm","posa1","hm+glasses"],
		
		["janna_p2_nrm","posa2","nrm+glasses"],
		["janna_p2_smi","posa2","smi+glasses"],
		["janna_p2_lau","posa2","lau+glasses"],
		["janna_p2_sur","posa2","sur+glasses"],
		["janna_p2_hm","posa2","hm+glasses"]
	];

	var avats = [
		["_janna_nrm","posa1","body+nrm+glasses+hairs2+hairs2_shadow"],
		["_janna_hm","posa1","body+hm+glasses+hairs2+hairs2_shadow"],
		["_janna_smi","posa1","body+smi+glasses+hairs2+hairs2_shadow"],
		["_janna_lau","posa1","body+lau+glasses+hairs2+hairs2_shadow"],
		["_janna_sur","posa1","body+sur+glasses+hairs2+hairs2_shadow"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

alert("Done!");
