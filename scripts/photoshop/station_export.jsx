//@include "libs/comixgen.jsx"
//@include "libs/persutils.jsx"

var globals = {};
initComix("d:/Downloads/export", globals);

//======================================================
var duppedDocument = null;

// Body
duppedDocument = cloneDocument(500, 500);
app.activeDocument = duppedDocument;
switchScene(null,"station");
exportSprite("station");
duppedDocument.close(SaveOptions.DONOTSAVECHANGES);

var parts = [["flyers","fly1"], ["flyers","fly2"], ["mipmops","mip1"],["mipmops","mip2"], ["mipmops","mip3"], ["mipmops","mip4"]];
for(var i=0;i < parts.length;i++){
	duppedDocument = cloneDocument(500, 500);
	app.activeDocument = duppedDocument;
	exportSpriteWithRelOffset(parts[i][0], null, parts[i][1]);
	duppedDocument.close(SaveOptions.DONOTSAVECHANGES);
}

alert("Done!");

