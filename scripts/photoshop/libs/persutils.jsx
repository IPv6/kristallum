//@include "comixgen.jsx"
//======================================================
function exportCharacter(bodies, emots, avats, charTag, scaleFactor, pathPref, jsonprefx){
	var AvatarBounds = getLayerByName(app.activeDocument, "AvatarBounds", null, null);
	if(AvatarBounds == null){
		alert("AvatarBounds layer not found, quitting");
		return;
	}
	var PersBounds = getLayerByName(app.activeDocument, "PersBounds", null, null);
	if(PersBounds == null){
		alert("PersBounds layer not found, quitting");
		return;
	}
	if(!pathPref){
		pathPref = "<path>";
	}
	var duppedDocument = null;
	var json_cnt = "{\n\t\"refs_pers\": {";
	json_cnt+="\n";

	if(avats != null){
		for(var i=0;i < avats.length;i++){
			duppedDocument = cloneDocument();
			app.activeDocument = duppedDocument;

			// Making group, masked by AvatarBounds layer
			var AvatarBounds = getLayerByName(app.activeDocument, "AvatarBounds", null, null);
			var AvatarMasked = app.activeDocument.layerSets.add();
			AvatarMasked.name = "AvatarMasked";
			app.activeDocument.activeLayer = AvatarBounds;
			activel_makeSelFromLayesTrp();
			app.activeDocument.activeLayer = AvatarMasked;
			activel_makeMaskFromSel('RvlS');

			// Moving parts
			switchScene(null, null);
			var avt_layers = switchScene(avats[i][1],avats[i][2],null,true);
			avt_layers = avt_layers.reverse();
			moveLayersInsideGroup("AvatarMasked", avt_layers);
			cropToLayerBoundsAndResize("AvatarBounds",100,100);
			var filename = exportSprite(avats[i][0]);
			duppedDocument.close(SaveOptions.DONOTSAVECHANGES);
			json_cnt+="\t\t\""+avats[i][0]+"\": \"" + pathPref + charTag+"/"+filename+"\",";
			json_cnt+="\n";
		}
	}

	duppedDocument = cloneDocument();
	app.activeDocument = duppedDocument;
	cropToLayerBoundsAndResize("PersBounds",null,null,scaleFactor);
	if(bodies != null){
		for(var i=0;i < bodies.length;i++){
			switchScene(null, null);
			switchScene(bodies[i][1],bodies[i][2],null,true);
			var filename = exportSprite(bodies[i][0]);
			json_cnt+="\t\t\""+bodies[i][0]+"\": \""+pathPref + charTag+"/"+filename+"\",";
			json_cnt+="\n";
		}
	}

	if(emots != null){
		//json_cnt+="\n";
		for(var i=0;i < emots.length;i++){
			var duppedDocument2 = cloneDocument(null,null,duppedDocument);
			app.activeDocument = duppedDocument2;
			switchScene(null, null);
			var filename = exportSpriteWithRelOffset(emots[i][0], emots[i][1], emots[i][2]);
			duppedDocument2.close(SaveOptions.DONOTSAVECHANGES);
			json_cnt+="\t\t\""+emots[i][0]+"\": \"" + pathPref + charTag+"/"+filename+"\",";
			json_cnt+="\n";
		}
	}
	duppedDocument.close(SaveOptions.DONOTSAVECHANGES);
	json_cnt += "\t\t\"hash_"+charTag+"\": \"...\"";
	json_cnt += "\n\t}\n}";
	saveText(jsonprefx+"_defns.json",json_cnt);
}
