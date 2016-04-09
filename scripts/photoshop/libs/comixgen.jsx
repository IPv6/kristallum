// enable double clicking from the Macintosh Finder or the Windows Explorer
#target photoshop

var globals = {};
var exportPath = null;
var currentSpeakSet = null;
var xlayers_cache = null;
var initialBaseDocument = null;

function initComix(_path_out, _globals) {
	if(_globals){
		globals = _globals;
	}
	initialBaseDocument = app.activeDocument;
	exportPath = _path_out;
	var exportFile = new Folder(exportPath);
	if(!exportFile.exists){
		exportFile.create();
	}
	globals.pageIndex = 0;
	if ( app.documents.length <= 0 ) {
		if ( DialogModes.NO != app.playbackDisplayDialogs ) {
			alert( "Document Must Be Opened");
		}
		return false;
	}
	app.preferences.interpolation = ResampleMethod.BICUBIC;
	app.activeDocument.changeMode(ChangeMode.RGB);
	return true;
}

////////////////////////////////////////////////////////////////////
function cloneDocument(ww, hh, origin) {
	xlayers_cache = null;
	var duppedDocument = origin?origin.duplicate():initialBaseDocument.duplicate();
	if(ww && hh){
		duppedDocument.resizeImage(UnitValue(ww,"px"),UnitValue(hh,"px"));
	}
	return duppedDocument;
}

function switchScene(layersParentName, visibleLayerName, speakSet, rasterizeEffectLayers) {
	var visibs = [];
	var rootset = null;
	if(layersParentName == null){
		rootset = app.activeDocument;
	}else{
		rootset = getLayerByName(app.activeDocument, layersParentName, null, null);
		if(rootset == null){
			alert("Cant say: not founds ["+layersParentName+"]");
			return visibs;
		}
		rootset.visible = true;
	}
	if(speakSet){
		currentSpeakSet = speakSet;
	}
	var names = [];
	if(visibleLayerName != null){
		names = visibleLayerName.split("+");
	}

	var layers      = getLayersByName(rootset, null, null, null);// was: rootset.layers without recrusion
		layerLen    = layers.length;
	//var dbg			= "";
	//for (var i = 0; i < layerLen; i++) {
	//	var layer       = layers[i];
	//	dbg += layer.name+",";
	//}
	//alert(""+layersParentName+":"+visibleLayerName+": Comparing ["+names.join("|")+"] vs ["+dbg+"]");
	for (var i = 0; i < layerLen; i++) {
		layers[i].visible = false;
	}
	for (var j = 0; j < names.length; j++) {
		var isFound = 0;
		var vislayer_name = names[j];
		for (var i = 0; i < layerLen; i++) {
			var layer = layers[i];
			if(vislayer_name == layer.name){
				isFound++;
				setLayerVisiblityWithParents(layer,true);//layer.visible = true;
				if(rasterizeEffectLayers){
					app.activeDocument.activeLayer = layer;
					if(activel_getLayerEffects(true).length > 0){
						activel_rasterizeEffects();
					}
				}
				visibs.push(layer);
			}
		}
		if(isFound != 1){
			alert(""+layersParentName+":"+visibleLayerName+": bad layer "+vislayer_name+", usecount="+isFound);
		}
	}
	return visibs;
}

function setLayerVisiblityWithParents(layer, newvis) {
	layer.visible = newvis;
	if(layer.parent != null && layer.parent.visible != newvis){
		setLayerVisiblityWithParents(layer.parent,newvis);
	}
}

function moveLayersInsideGroup(newrootName, layersToMove) {
	var prnt = getLayerByName(app.activeDocument,newrootName,null,null);
	prnt.visible = true;
	//alert(prnt + " " + prnt.typename + " " + prnt.layers);
	var nullgrp = prnt.layerSets.add();
	var nulllay = nullgrp.artLayers.add();
	for(var i = 0; i<layersToMove.length; i++){
		layersToMove[i].move(nulllay, ElementPlacement.PLACEBEFORE);
	}
	//nullgrp.merge();
	return prnt;
}

function getLayerId(layer) {
	return layer.name+"."+(layer.parent != null?getLayerId(layer.parent):"");
}

function getLayersByName(target, name, namepart, ofKind) {
	// this basically loops all the layers to find
	//alert("ln=["+target.name+"] id="+getLayerId(target));
	var cache_key = "cc"+getLayerId(target)+"_"+(name?name:"")+"_"+(namepart?namepart:"")+"_"+(ofKind?ofKind:"");
	if(!xlayers_cache){
		xlayers_cache = {};
	}
	if(xlayers_cache[cache_key] != null){
		return xlayers_cache[cache_key];
	}
	var result = [];
	if (target == null){
		return result;
	}
	var layers      = target.layers,
		layerLen    = layers.length;
	for (var i = 0; i < layerLen; i++) {
		var layer       = layers[i];
		var isLayerSet  = layer.typename == 'LayerSet';
		var isValid     = (name == null && namepart == null) || (name != null && layer.name == name) 
			|| (namepart != null && layer.name.indexOf(namepart) >= 0);
		if(ofKind != null && layer.kind != ofKind){//LayerKind.TEXT
			isValid = false;
		}
		if(isValid){
			result.push(layer);
		}
		if (isLayerSet) {
			var found_layers = getLayersByName(layer, name, namepart, ofKind);
			if (found_layers.length > 0) {
				result = result.concat(found_layers);
			}
		}
	}
	xlayers_cache[cache_key] = result;
	return result;
}

function getLayerByName(target, name, namepart, ofKind) {
	var layers = getLayersByName(target, name, namepart, ofKind);
	if(layers.length>0){
		return layers[0];
	}
	return null;
}

function getBoundsCenter(lr_bounds) {
	var x = lr_bounds[0].value;
	var y = lr_bounds[1].value;
	var height = (lr_bounds[3]-lr_bounds[1]).value;
	var width = (lr_bounds[2]-lr_bounds[0]).value;
	return [Math.floor(x+width/2),Math.floor(y+height/2)];
}

function cropToLayerBoundsAndResize(prefix,ww,hh,scale) {
	if(prefix){
		var prnt = getLayerByName(app.activeDocument,prefix,null,null);
		if(prnt){
			app.activeDocument.crop(prnt.bounds);
		}
	}
	if(ww && hh){
		app.activeDocument.resizeImage(UnitValue(ww,"px"),UnitValue(hh,"px"));
	}
	if(scale){
		ww = app.activeDocument.width.value*scale;
		hh = app.activeDocument.height.value*scale;
		app.activeDocument.resizeImage(UnitValue(ww,"px"),UnitValue(hh,"px"));
	}
}

function activel_makeMaskFromSel(maskType) {
	// https://forums.adobe.com/thread/290125?start=0&tstart=0
	if( maskType == undefined) maskType = 'RvlS' ; //from selection
	//requires a selection 'RvlS'  complete mask 'RvlA' otherThanSelection 'HdSl'
    var desc140 = new ActionDescriptor();
    desc140.putClass( charIDToTypeID('Nw  '), charIDToTypeID('Chnl') );
        var ref51 = new ActionReference();
        ref51.putEnumerated( charIDToTypeID('Chnl'), charIDToTypeID('Chnl'), charIDToTypeID('Msk ') );
    desc140.putReference( charIDToTypeID('At  '), ref51 );
    desc140.putEnumerated( charIDToTypeID('Usng'), charIDToTypeID('UsrM'), charIDToTypeID(maskType) );
    executeAction( charIDToTypeID('Mk  '), desc140, DialogModes.NO );
}

function activel_makeSelFromLayesTrp()
{
	// http://stackoverflow.com/questions/17531731/setting-selection-to-layer-transparency-channel-using-extendscript-in-photoshop
    var idChnl = charIDToTypeID( "Chnl" );
    var actionSelect = new ActionReference();
    actionSelect.putProperty( idChnl, charIDToTypeID( "fsel" ) );     
    var actionTransparent = new ActionReference();    
    actionTransparent.putEnumerated( idChnl, idChnl, charIDToTypeID( "Trsp" ) );
    var actionDesc = new ActionDescriptor();
    actionDesc.putReference( charIDToTypeID( "null" ), actionSelect );
    actionDesc.putReference( charIDToTypeID( "T   " ), actionTransparent );
    executeAction( charIDToTypeID( "setd" ), actionDesc, DialogModes.NO );
}

function activel_getLayerEffects(getFirstOnly)
{
	var ref = new ActionReference();  
	ref.putEnumerated( charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt") );  
	var desc = executeActionGet(ref);  
	if ( desc.hasKey( stringIDToTypeID( 'layerEffects' ) ) ) {  
		var effects = [];  
		var effectDesc = desc.getObjectValue(  stringIDToTypeID( 'layerEffects' ) );  
		// first key is scale so skip and start with 1  
		for ( var effect = 1; effect < effectDesc.count; effect++ ) {  
			effects.push( typeIDToStringID( effectDesc.getKey( effect ) ) );  
			if(getFirstOnly){
				break;
			}
		}  
		return effects;  
	}
	return [];
}

function activel_rasterizeEffects()
{
	var idrasterizeLayer = stringIDToTypeID( "rasterizeLayer" );
	var desc5 = new ActionDescriptor();
	var idnull = charIDToTypeID( "null" );
	var ref4 = new ActionReference();
	var idLyr = charIDToTypeID( "Lyr " );
	var idOrdn = charIDToTypeID( "Ordn" );
	var idTrgt = charIDToTypeID( "Trgt" );
	ref4.putEnumerated( idLyr, idOrdn, idTrgt );
	desc5.putReference( idnull, ref4 );
	var idWhat = charIDToTypeID( "What" );
	var idrasterizeItem = stringIDToTypeID( "rasterizeItem" );
	var idlayerStyle = stringIDToTypeID( "layerStyle" );
	desc5.putEnumerated( idWhat, idrasterizeItem, idlayerStyle );
	executeAction( idrasterizeLayer, desc5, DialogModes.NO );
}

if (typeof Array.prototype.indexOf != "function") {  
	Array.prototype.indexOf = function (el) {  
		for(var i = 0; i < this.length; i++) {
			if(el === this[i]) {
				return i;
			}
		}
		return -1;  
	}  
}

/////////////////////////////////////////////////////////////
// Exporters
function say(layersParentName, visibleLayerName, text2say) {
	if(layersParentName == null && currentSpeakSet != null){
		layersParentName = currentSpeakSet[0];
	}
	if(visibleLayerName == null && currentSpeakSet != null){
		visibleLayerName = currentSpeakSet[1];
	}
	var rootset = getLayerByName(app.activeDocument, layersParentName, null, null);
	if(rootset == null){
		alert("Cant say: not founs ["+layersParentName+"]");
		return;
	}
	var layers      = rootset.layers,
		layerLen    = layers.length;
	for (var i = 0; i < layerLen; i++) {
		var layer       = layers[i];
		if(visibleLayerName != null && text2say != null && layer.name == visibleLayerName){
			layer.visible = true;
			layer.textItem.contents = text2say;
			//layer.textItem.width = 700;
		}else{
			layer.visible = false;
		}
	}
	globals.pageIndex++;
	exportPage(globals.pageIndex);
}

function int2str(numb, padzerosize){var res = ""+numb;while(res.length < padzerosize){res = "0"+res;}return res;}
function exportPage(page_index) {
	var saveFileName = exportPath +"/page_"+int2str(page_index,3)+".jpg";
	var saveFile = new File(saveFileName);
	if(saveFile.exists){
		saveFile.remove();
	}
	//alert("Saving "+saveFileName);
	var pngOpts = new ExportOptionsSaveForWeb; 
	pngOpts.format = SaveDocumentType.JPEG;
	pngOpts.quality = 80;
	activeDocument.exportDocument(saveFile,ExportType.SAVEFORWEB,pngOpts); 
}


function exportSprite(prefix) {
	var w = app.activeDocument.width.value;//toString().replace(' px', '');
	var h = app.activeDocument.height.value;//toString().replace(' px', '');
	var saveFileNamePp = prefix+"_ww"+w+"_hh"+h+".png";
	var saveFileName = exportPath +"/"+saveFileNamePp;
	var saveFile = new File(saveFileName);
	if(saveFile.exists){
		saveFile.remove();
	}
	//alert("Saving "+saveFileName);
	var pngOpts = new ExportOptionsSaveForWeb; 
	pngOpts.format = SaveDocumentType.PNG;
	pngOpts.PNG8 = false; 
	pngOpts.transparency = true; 
	pngOpts.interlaced = false; 
	activeDocument.exportDocument(saveFile,ExportType.SAVEFORWEB,pngOpts); 
	return saveFileNamePp;
}

function exportSpriteWithRelOffset(prefix, group1, group2) {
	var ad_bounds = [UnitValue(0,"px"),UnitValue(0,"px"),app.activeDocument.width,app.activeDocument.height];
	var layers = switchScene(group1, group2, null, true);
	if(layers == null || layers.length == 0){
		return;
	}
	var lr_bounds = layers[0].bounds;
	for(var i=1;i<layers.length;i++){
		var tbn = layers[1].bounds;
		if(tbn[0].value < lr_bounds[0].value){
			lr_bounds[0].value = tbn[0].value;
		}
		if(tbn[1].value < lr_bounds[1].value){
			lr_bounds[1].value = tbn[1].value;
		}
		if(tbn[2].value > lr_bounds[2].value){
			lr_bounds[2].value = tbn[2].value;
		}
		if(tbn[3].value > lr_bounds[3].value){
			lr_bounds[3].value = tbn[3].value;
		}
	}
	//alert("exportSpriteWithRelOffset: "+prefix+"/"+group1+"/"+group2+": "+getLayerId(layers[0]));
	app.activeDocument.crop(lr_bounds);
	var ssp = prefix+
		"_ox"+(getBoundsCenter(lr_bounds)[0]-getBoundsCenter(ad_bounds)[0])+
		"_oy"+(getBoundsCenter(lr_bounds)[1]-getBoundsCenter(ad_bounds)[1]);
	return exportSprite(ssp);
}

function saveText(filename,text) {
	var saveFileName = exportPath +"/"+filename;
	var saveFile = new File(saveFileName);
	if(saveFile.exists){
		saveFile.remove();
	}
	saveFile.open("w", "TEXT");  
	saveFile.writeln(text);  
	saveFile.close(); 
}