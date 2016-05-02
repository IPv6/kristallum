//@include "libs/comixgen.jsx"
//@include "libs/persutils.jsx"

//var exportTo = "gena";
//var exportTo = "anna";
//var exportTo = "vera";
//var exportTo = "belpoli";
//var exportTo = "marina";
//var exportTo = "kasatka";
//var exportTo = "janna";
var exportTo = "sasha";
//var exportTo = "artem";
//var exportTo = "anton";
//var exportTo = "ura";
//var exportTo = "samanta";
//var exportTo = "katya";

//var exportTo = "prof";
//var exportTo = "tamojk";
//var exportTo = "prodalx";


var globals = {};
initComix("d:/Downloads/"+exportTo, globals);

//======================================================
var duppedDocument = null;
var json_cnt = "";
switchScene(null, null);
var scaleFactor = 0.58; //0.71145833333 - 2048 problem;// 1920->1366
var refs_path = "/vn_storyline/art/pers2/";

if(exportTo == "prodalx"){

	var bodies = [
		["prodalx_p1_dress1","posa1","body+dress1"],
		["prodalx_p1_dress2","posa1","body+dress2"],
	];

	// Emotions prodalx
	var emots = [
		["prodalx_p1_nrm","posa1","nrm"],
		["prodalx_p1_smi","posa1","smi"],
		["prodalx_p1_lau","posa1","lau"],
		["prodalx_p1_sur","posa1","sur"],
		["prodalx_p1_hm","posa1","hm"],
	];

	// Avatar prodalx
	var avats = [
		["_prodalx_nrm","posa1","body+nrm"],
		["_prodalx_smi","posa1","body+smi"],
		["_prodalx_lau","posa1","body+lau"],
		["_prodalx_sur","posa1","body+sur"],
		["_prodalx_hm","posa1","body+hm"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

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
		["prof_p1_dress1","posa1","body+dress1+hairs"],
		["prof_p1_dress2","posa1","body+dress2+hairs"],
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
		["sasha_p1_dress1","posa1","body+body_part3+dress1+hairs1+hairs2+hairs2_shadow"],
		["sasha_p1_dress2","posa1","body+body_part3+dress2+hairs1+hairs2+hairs2_shadow"],
		["sasha_p2_dress1","posa2","body+body_part3+dress1+hairs1+hairs2+hairs2_shadow"],
		["sasha_p2_dress2","posa2","body+body_part3+dress2+hairs1+hairs2+hairs2_shadow"],
		["sasha_p3_dress1","posa3","body+body_part3+dress1+hairs1+hairs2+hairs2_shadow"],
		["sasha_p3_dress2","posa3","body+body_part3+dress2+hairs1+hairs2+hairs2_shadow"],
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
		["sasha_p2_sur","posa2","sur"],
		
		["sasha_p3_nrm","posa3","nrm"],
		["sasha_p3_smi","posa3","smi"],
		["sasha_p3_lau","posa3","lau"],
		["sasha_p3_hm","posa3","hm"],
		["sasha_p3_sur","posa3","sur"],
	];

	// Avatar sasha
	var avats = [
		["_sasha_nrm","posa1","hairs1+body+body_part3+nrm+hairs2"],
		["_sasha_hm","posa1","hairs1+body+body_part3+hm+hairs2"],
		["_sasha_smi","posa1","hairs1+body+body_part3+smi+hairs2"],
		["_sasha_lau","posa1","hairs1+body+body_part3+lau+hairs2"],
		["_sasha_sur","posa1","hairs1+body+body_part3+sur+hairs2"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}


if(exportTo == "samanta"){

	var bodies = [
		["samanta_p1_dress1","posa1","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["samanta_p1_dress2","posa1","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["samanta_p2_dress1","posa2","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["samanta_p2_dress2","posa2","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["samanta_p3_dress1","posa3","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["samanta_p3_dress2","posa3","hairs1+body+dress2+hairs2+hairs2_shadow"],
	];

	var emots = [
		["samanta_p1_nrm","posa1","nrm"],
		["samanta_p1_smi","posa1","smi"],
		["samanta_p1_lau","posa1","lau"],
		["samanta_p1_sur","posa1","sur"],
		["samanta_p1_hm","posa1","hm"],
		["samanta_p1_shy","posa1","shy"],
		
		["samanta_p2_nrm","posa2","nrm"],
		["samanta_p2_smi","posa2","smi"],
		["samanta_p2_lau","posa2","lau"],
		["samanta_p2_sur","posa2","sur"],
		["samanta_p2_hm","posa2","hm"],
		["samanta_p2_shy","posa2","shy"],
		
		["samanta_p3_nrm","posa3","nrm"],
		["samanta_p3_smi","posa3","smi"],
		["samanta_p3_lau","posa3","lau"],
		["samanta_p3_sur","posa3","sur"],
		["samanta_p3_hm","posa3","hm"],
		["samanta_p3_shy","posa3","shy"],
	];

	var avats = [
		["_samanta_nrm","posa1","hairs1+body+hairs2+nrm"],
		["_samanta_hm","posa1","hairs1+body+hairs2+hm"],
		["_samanta_smi","posa1","hairs1+body+hairs2+smi"],
		["_samanta_lau","posa1","hairs1+body+hairs2+lau"],
		["_samanta_sur","posa1","hairs1+body+hairs2+sur"],
		["_samanta_shy","posa1","hairs1+body+hairs2+shy"],
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "belpoli"){

	var bodies = [
		["bpl_p1_dress1","posa1","body+dress1+hairs2+hairs2_shadow"],
		["bpl_p1_dress2","posa1","body+dress2+hairs2+hairs2_shadow"],
		["bpl_p2_dress1","posa2","body+dress1+hairs2+hairs2_shadow"],
		["bpl_p2_dress2","posa2","body+dress2+hairs2+hairs2_shadow"],
		["bpl_p3a_dress1","posa3","body+body_part2_1+dress1+hairs2+hairs2_shadow+dress1_part2"],
		["bpl_p3a_dress2","posa3","body+body_part2_1+dress2+hairs2+hairs2_shadow"],
		["bpl_p3b_dress1","posa3","body+body_part2_2+dress1+hairs2+hairs2_shadow+dress1_part2"],
		["bpl_p3b_dress2","posa3","body+body_part2_2+dress2+hairs2+hairs2_shadow"],
		["bpl_p3c_dress1","posa3","body+body_part2_3+dress1+hairs2+hairs2_shadow+dress1_part2"],
		["bpl_p3c_dress2","posa3","body+body_part2_3+dress2+hairs2+hairs2_shadow"],
	];

	var emots = [
		["bpl_p1_nrm","posa1","nrm"],
		["bpl_p1_smi","posa1","smi"],
		["bpl_p1_smi_z","posa1","smi_z"],
		["bpl_p1_lau","posa1","lau"],
		["bpl_p1_sur","posa1","sur"],
		["bpl_p1_hm","posa1","hm"],
		["bpl_p1_drim","posa1","drim"],
		
		["bpl_p2_nrm","posa2","nrm"],
		["bpl_p2_smi","posa2","smi"],
		["bpl_p2_smi_z","posa2","smi_z"],
		["bpl_p2_lau","posa2","lau"],
		["bpl_p2_sur","posa2","sur"],
		["bpl_p2_hm","posa2","hm"],
		["bpl_p2_drim","posa2","drim"],
		
		["bpl_p3a_nrm","posa3","nrm"],
		["bpl_p3a_smi","posa3","smi"],
		["bpl_p3a_smi_z","posa3","smi_z"],
		["bpl_p3a_lau","posa3","lau"],
		["bpl_p3a_sur","posa3","sur"],
		["bpl_p3a_hm","posa3","hm"],
		["bpl_p3a_drim","posa3","drim"],
		
		["bpl_p3b_nrm","posa3","nrm"],
		["bpl_p3b_smi","posa3","smi"],
		["bpl_p3b_smi_z","posa3","smi_z"],
		["bpl_p3b_lau","posa3","lau"],
		["bpl_p3b_sur","posa3","sur"],
		["bpl_p3b_hm","posa3","hm"],
		["bpl_p3b_drim","posa3","drim"],
		
		["bpl_p3c_nrm","posa3","nrm"],
		["bpl_p3c_smi","posa3","smi"],
		["bpl_p3c_smi_z","posa3","smi_z"],
		["bpl_p3c_lau","posa3","lau"],
		["bpl_p3c_sur","posa3","sur"],
		["bpl_p3c_hm","posa3","hm"],
		["bpl_p3c_drim","posa3","drim"],
	];

	var avats = [
		["_bpl_nrm","posa1","body+hairs2+nrm"],
		["_bpl_hm","posa1","body+hairs2+hm"],
		["_bpl_smi","posa1","body+hairs2+smi"],
		["_bpl_smi_z","posa1","body+hairs2+smi_z"],
		["_bpl_lau","posa1","body+hairs2+lau"],
		["_bpl_sur","posa1","body+hairs2+sur"],
		["_bpl_drim","posa1","body+hairs2+drim"],
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "anna"){

	var bodies = [
		["anna_p1_dress1","posa1","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["anna_p1_dress2","posa1","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["anna_p2_dress1","posa2","hairs1+body+dress1+hairs2+hairs2_shadow"],//+body_part2
		["anna_p2_dress2","posa2","hairs1+body+dress2+hairs2+hairs2_shadow"],//+body_part2
		["anna_p3_dress1","posa3","hairs1+body+dress1+hairs2+hairs2_shadow"],//+body_part2
		["anna_p3_dress2","posa3","hairs1+body+dress2+hairs2+hairs2_shadow"],//+body_part2
		["anna_p4_dress1","posa4","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["anna_p4_dress2","posa4","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["anna_p5_dress1","posa5","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["anna_p5_dress2","posa5","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["anna_p6_dress1","posa6","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["anna_p6_dress2","posa6","hairs1+body+dress2+hairs2+hairs2_shadow"],
	];

	var emots = [
		["anna_p1_nrm","posa1","nrm"],
		["anna_p1_smi","posa1","smi"],
		["anna_p1_smi_z","posa1","smi_z"],
		["anna_p1_lau","posa1","lau"],
		["anna_p1_sur","posa1","sur"],
		["anna_p1_hm","posa1","hm"],
		["anna_p1_hm_z","posa1","hm_z"],
		["anna_p1_hate","posa1","hate"],
		["anna_p1_drim","posa1","drim"],
		["anna_p1_wtf","posa1","wtf"],
		
		["anna_p2_nrm","posa2","nrm"],
		["anna_p2_smi","posa2","smi"],
		["anna_p2_smi_z","posa2","smi_z"],
		["anna_p2_lau","posa2","lau"],
		["anna_p2_sur","posa2","sur"],
		["anna_p2_hm_z","posa2","hm_z"],
		["anna_p2_hm","posa2","hm"],
		["anna_p2_hate","posa2","hate"],
		["anna_p2_drim","posa2","drim"],
		["anna_p2_wtf","posa2","wtf"],
		
		["anna_p3_nrm","posa3","nrm"],
		["anna_p3_smi","posa3","smi"],
		["anna_p3_smi_z","posa3","smi_z"],
		["anna_p3_lau","posa3","lau"],
		["anna_p3_sur","posa3","sur"],
		["anna_p3_hm_z","posa3","hm_z"],
		["anna_p3_hm","posa3","hm"],
		["anna_p3_hate","posa3","hate"],
		["anna_p3_drim","posa3","drim"],
		["anna_p3_wtf","posa3","wtf"],
		
		["anna_p4_nrm","posa4","nrm"],
		["anna_p4_smi","posa4","smi"],
		["anna_p4_smi_z","posa4","smi_z"],
		["anna_p4_lau","posa4","lau"],
		["anna_p4_sur","posa4","sur"],
		["anna_p4_hm_z","posa4","hm_z"],
		["anna_p4_hm","posa4","hm"],
		["anna_p4_hate","posa4","hate"],
		["anna_p4_drim","posa4","drim"],
		["anna_p4_wtf","posa4","wtf"],
		
		["anna_p5_nrm","posa5","nrm"],
		["anna_p5_smi","posa5","smi"],
		["anna_p5_smi_z","posa5","smi_z"],
		["anna_p5_lau","posa5","lau"],
		["anna_p5_sur","posa5","sur"],
		["anna_p5_hm_z","posa5","hm_z"],
		["anna_p5_hm","posa5","hm"],
		["anna_p5_hate","posa5","hate"],
		["anna_p5_drim","posa5","drim"],
		["anna_p5_wtf","posa5","wtf"],
		
		["anna_p6_nrm","posa6","nrm"],
		["anna_p6_smi","posa6","smi"],
		["anna_p6_smi_z","posa6","smi_z"],
		["anna_p6_lau","posa6","lau"],
		["anna_p6_sur","posa6","sur"],
		["anna_p6_hm_z","posa6","hm_z"],
		["anna_p6_hm","posa6","hm"],
		["anna_p6_hate","posa6","hate"],
		["anna_p6_drim","posa6","drim"],
		["anna_p6_wtf","posa6","wtf"],
	];

	var avats = [
		["_anna_nrm","posa1","hairs1+body+hairs2+nrm"],
		["_anna_hm","posa1","hairs1+body+hairs2+hm"],
		["_anna_hm_z","posa1","hairs1+body+hairs2+hm_z"],
		["_anna_smi","posa1","hairs1+body+hairs2+smi"],
		["_anna_smi_z","posa1","hairs1+body+hairs2+smi_z"],
		["_anna_lau","posa1","hairs1+body+hairs2+lau"],
		["_anna_sur","posa1","hairs1+body+hairs2+sur"],
		["_anna_hate","posa1","hairs1+body+hairs2+hate"],
		["_anna_drim","posa1","hairs1+body+hairs2+drim"],
		["_anna_wtf","posa1","hairs1+body+hairs2+wtf"]
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
		["vera_p3_dress1","posa3","body+dress1+hairs2+hairs2_shadow+hairs3_dress1"],
		["vera_p3_dress2","posa3","body+dress2+hairs2+hairs2_shadow+hairs3_dress2"],
		["vera_p4_dress1","posa4","body+dress1+hairs2+hairs2_shadow+hairs3_dress1"],
		["vera_p4_dress2","posa4","body+dress2+hairs2+hairs2_shadow+hairs3_dress2"],
	];

	var emots = [
		["vera_p1_nrm","posa1","nrm"],
		["vera_p1_smi","posa1","smi"],
		["vera_p1_lau","posa1","lau"],
		["vera_p1_sur","posa1","sur"],
		["vera_p1_hm","posa1","hm"],
		["vera_p1_rage","posa1","rage"],
		["vera_p1_rage_z","posa1","rage_z"],
		
		["vera_p2_nrm","posa2","nrm"],
		["vera_p2_smi","posa2","smi"],
		["vera_p2_lau","posa2","lau"],
		["vera_p2_sur","posa2","sur"],
		["vera_p2_hm","posa2","hm"],
		["vera_p2_rage","posa2","rage"],
		["vera_p2_rage_z","posa2","rage_z"],
		
		["vera_p3_nrm","posa3","nrm"],
		["vera_p3_smi","posa3","smi"],
		["vera_p3_lau","posa3","lau"],
		["vera_p3_sur","posa3","sur"],
		["vera_p3_hm","posa3","hm"],
		["vera_p3_rage","posa3","rage"],
		["vera_p3_rage_z","posa3","rage_z"],
		
		["vera_p4_nrm","posa4","nrm"],
		["vera_p4_smi","posa4","smi"],
		["vera_p4_lau","posa4","lau"],
		["vera_p4_sur","posa4","sur"],
		["vera_p4_hm","posa4","hm"],
		["vera_p4_rage","posa4","rage"],
		["vera_p4_rage_z","posa4","rage_z"],
	];

	var avats = [
		["_vera_nrm","posa1","body+hairs2+nrm"],
		["_vera_smi","posa1","body+hairs2+smi"],
		["_vera_lau","posa1","body+hairs2+lau"],
		["_vera_sur","posa1","body+hairs2+sur"],
		["_vera_hm","posa1","body+hairs2+hm"],
		["_vera_rage","posa1","body+hairs2+rage"],
		["_vera_rage_z","posa1","body+hairs2+rage_z"],
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "kasatka"){

	var bodies = [
		["kasatka_p1_dress1","posa1","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["kasatka_p1_dress2","posa1","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["kasatka_p2_dress1","posa2","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["kasatka_p2_dress2","posa2","hairs1+body+dress2+hairs2+hairs2_shadow"],
		["kasatka_p3_dress1","posa3","hairs1+body+dress1+hairs2+hairs2_shadow"],
		["kasatka_p3_dress2","posa3","hairs1+body+dress2+hairs2+hairs2_shadow"],
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
		["kasatka_p2_hm","posa2","hm"],
		
		["kasatka_p3_nrm","posa3","nrm"],
		["kasatka_p3_smi","posa3","smi"],
		["kasatka_p3_lau","posa3","lau"],
		["kasatka_p3_sur","posa3","sur"],
		["kasatka_p3_hm","posa3","hm"],
	];

	var avats = [
		["_kasatka_nrm","posa1","hairs1+body+hairs2+nrm"],
		["_kasatka_hm","posa1","hairs1+body+hairs2+hm"],
		["_kasatka_smi","posa1","hairs1+body+hairs2+smi"],
		["_kasatka_lau","posa1","hairs1+body+hairs2+lau"],
		["_kasatka_sur","posa1","hairs1+body+hairs2+sur"],
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

if(exportTo == "marina"){

	var bodies = [
		["marina_p1_dress1","posa1","hairs3b+hairs3a+body+dress1+hairs2a+hairs2_shadow"],
		["marina_p1_dress2","posa1","hairs4b+body+dress2+hairs2a+hairs2_shadow"],
		["marina_p1_dress3","posa1","hairs5b+body+dress3+hairs2a+hairs2_shadow"],
		["marina_p1_dress4","posa1","hairs5b+body+dress4+hairs2a+hairs2_shadow"],

		["marina_p2_dress1","posa2","hairs3b+hairs3a+body+dress1+hairs2a+hairs2_shadow"],
		["marina_p2_dress2","posa2","hairs4b+body+dress2+hairs2a+hairs2_shadow"],
		["marina_p2_dress3","posa2","hairs5b+body+dress3+hairs2a+hairs2_shadow"],
		["marina_p2_dress4","posa2","hairs5b+body+dress4+hairs2a+hairs2_shadow"],
		
		["marina_p3_dress1","posa3","hairs3b+hairs3a+body+dress1+hairs2a+hairs2_shadow"],
		["marina_p3_dress2","posa3","hairs4b+body+dress2+hairs2a+hairs2_shadow"],
		["marina_p3_dress3","posa3","hairs5b+body+dress3+hairs2a+hairs2_shadow"],
		["marina_p3_dress4","posa3","hairs5b+body+dress4+hairs2a+hairs2_shadow"],
		
		["marina_p4_dress1","posa4","hairs3b+hairs3a+body+dress1+hairs2a+hairs2_shadow"],
		["marina_p4_dress2","posa4","hairs4b+body+dress2+hairs2a+hairs2_shadow"],
		["marina_p4_dress3","posa4","hairs5b+body+dress3+hairs2a+hairs2_shadow"],
		["marina_p4_dress4","posa4","hairs5b+body+dress4+hairs2a+hairs2_shadow"],
		
		["marina_p5_dress1","posa5","hairs3b+hairs3a+body+body_part2+dress1+hairs2a+hairs2_shadow"],
		["marina_p5_dress2","posa5","hairs4b+body+body_part2+dress2+dress2_part2+hairs2a+hairs2_shadow"],
		["marina_p5_dress3","posa5","hairs5b+body+body_part2+dress3+hairs2a+hairs2_shadow"],
		["marina_p5_dress4","posa5","hairs5b+body+body_part2+dress4+hairs2a+hairs2_shadow"],
	];

	var emots = [
		["marina_p1_nrm","posa1","nrm+hairs6b"],
		["marina_p1_smi","posa1","smi+hairs6b"],
		["marina_p1_lau","posa1","lau+hairs6b"],
		["marina_p1_sur","posa1","sur+hairs6b"],
		["marina_p1_hm","posa1","hm+hairs6b"],
		["marina_p1_nrm_z","posa1","nrm+hairs6a"],
		["marina_p1_smi_z","posa1","smi+hairs6a"],
		["marina_p1_lau_z","posa1","lau+hairs6a"],
		["marina_p1_sur_z","posa1","sur+hairs6a"],
		["marina_p1_hm_z","posa1","hm+hairs6a"],
		
		["marina_p2_nrm","posa2","nrm+hairs6b"],
		["marina_p2_smi","posa2","smi+hairs6b"],
		["marina_p2_lau","posa2","lau+hairs6b"],
		["marina_p2_sur","posa2","sur+hairs6b"],
		["marina_p2_hm","posa2","hm+hairs6b"],
		["marina_p2_nrm_z","posa2","nrm+hairs6a"],
		["marina_p2_smi_z","posa2","smi+hairs6a"],
		["marina_p2_lau_z","posa2","lau+hairs6a"],
		["marina_p2_sur_z","posa2","sur+hairs6a"],
		["marina_p2_hm_z","posa2","hm+hairs6a"],
		
		["marina_p3_nrm","posa3","nrm+hairs6b"],
		["marina_p3_smi","posa3","smi+hairs6b"],
		["marina_p3_lau","posa3","lau+hairs6b"],
		["marina_p3_sur","posa3","sur+hairs6b"],
		["marina_p3_hm","posa3","hm+hairs6b"],
		["marina_p3_nrm_z","posa3","nrm+hairs6a"],
		["marina_p3_smi_z","posa3","smi+hairs6a"],
		["marina_p3_lau_z","posa3","lau+hairs6a"],
		["marina_p3_sur_z","posa3","sur+hairs6a"],
		["marina_p3_hm_z","posa3","hm+hairs6a"],
		
		["marina_p4_nrm","posa4","nrm+hairs6b"],
		["marina_p4_smi","posa4","smi+hairs6b"],
		["marina_p4_lau","posa4","lau+hairs6b"],
		["marina_p4_sur","posa4","sur+hairs6b"],
		["marina_p4_hm","posa4","hm+hairs6b"],
		["marina_p4_nrm_z","posa4","nrm+hairs6a"],
		["marina_p4_smi_z","posa4","smi+hairs6a"],
		["marina_p4_lau_z","posa4","lau+hairs6a"],
		["marina_p4_sur_z","posa4","sur+hairs6a"],
		["marina_p4_hm_z","posa4","hm+hairs6a"],
		
		["marina_p5_nrm","posa5","nrm+hairs6b"],
		["marina_p5_smi","posa5","smi+hairs6b"],
		["marina_p5_lau","posa5","lau+hairs6b"],
		["marina_p5_sur","posa5","sur+hairs6b"],
		["marina_p5_hm","posa5","hm+hairs6b"],
		["marina_p5_nrm_z","posa5","nrm+hairs6a"],
		["marina_p5_smi_z","posa5","smi+hairs6a"],
		["marina_p5_lau_z","posa5","lau+hairs6a"],
		["marina_p5_sur_z","posa5","sur+hairs6a"],
		["marina_p5_hm_z","posa5","hm+hairs6a"],
	];

	var avats = [
		["_marina_nrm","posa1","hairs3b+body+hairs2a+hairs3a+nrm+hairs6b"],
		["_marina_hm","posa1","hairs3b+body+hairs2a+hairs3a+hm+hairs6b"],
		["_marina_smi","posa1","hairs3b+body+hairs2a+hairs3a+smi+hairs6b"],
		["_marina_lau","posa1","hairs3b+body+hairs2a+hairs3a+lau+hairs6b"],
		["_marina_sur","posa1","hairs3b+body+hairs2a+hairs3a+sur+hairs6b"],
		["_marina_nrm_z","posa1","hairs3b+body+hairs2a+hairs3a+nrm+hairs6a"],
		["_marina_hm_z","posa1","hairs3b+body+hairs2a+hairs3a+hm+hairs6a"],
		["_marina_smi_z","posa1","hairs3b+body+hairs2a+hairs3a+smi+hairs6a"],
		["_marina_lau_z","posa1","hairs3b+body+hairs2a+hairs3a+lau+hairs6a"],
		["_marina_sur_z","posa1","hairs3b+body+hairs2a+hairs3a+sur+hairs6a"],
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
		["janna_p1_dress1","posa1","body+dress1+body_part2+hairs2+hairs2_shadow"],
		["janna_p2_dress1","posa2","body+dress1+hairs2+hairs2_shadow"],
		["janna_p3_dress1","posa3","body+dress1+hairs2+hairs2_shadow"],
		["janna_p4_dress1","posa4","body+dress1+body_part2+hairs2+hairs2_shadow"],
		["janna_p5_dress1","posa5","body+dress1+body_part2+hairs2+hairs2_shadow"],
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
		["janna_p2_hm","posa2","hm+glasses"],
		
		["janna_p3_nrm","posa3","nrm+glasses"],
		["janna_p3_smi","posa3","smi+glasses"],
		["janna_p3_lau","posa3","lau+glasses"],
		["janna_p3_sur","posa3","sur+glasses"],
		["janna_p3_hm","posa3","hm+glasses"],
		
		["janna_p4_nrm","posa4","nrm+glasses"],
		["janna_p4_smi","posa4","smi+glasses"],
		["janna_p4_lau","posa4","lau+glasses"],
		["janna_p4_sur","posa4","sur+glasses"],
		["janna_p4_hm","posa4","hm+glasses"],
		
		["janna_p5_nrm","posa5","nrm+glasses"],
		["janna_p5_smi","posa5","smi+glasses"],
		["janna_p5_lau","posa5","lau+glasses"],
		["janna_p5_sur","posa5","sur+glasses"],
		["janna_p5_hm","posa5","hm+glasses"],
	];

	var avats = [
		["_janna_nrm","posa1","body+nrm+glasses+hairs2"],
		["_janna_hm","posa1","body+hm+glasses+hairs2"],
		["_janna_smi","posa1","body+smi+glasses+hairs2"],
		["_janna_lau","posa1","body+lau+glasses+hairs2"],
		["_janna_sur","posa1","body+sur+glasses+hairs2"]
	];

	exportCharacter(bodies,emots,avats,exportTo,scaleFactor,refs_path,exportTo);
}

alert("Done!");
