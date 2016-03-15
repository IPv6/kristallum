// cscript "c:\_WPLabs\PROJECTS_GAMES\Dropbox\_docs\_tools\Scripts\mp3_beat_extract.js" "c:\_WPLabs\PROJECTS_GAMES\Dropbox\web-static\static-ldu\vn_storyline\music2"
// cscript "c:\_WPLabs\PROJECTS_GAMES\Dropbox\_docs\_tools\Scripts\mp3_beat_extract.js" "c:\_WPLabs\PROJECTS_GAMES\Dropbox\web-static\static-ldu\station"

// c:\_WPLabs\_Portable\SonicAnnot\sonic-annotator.exe -t beat-extract.rdf -w json d:\Downloads\bg_virtv2_bb.mp3

//WScript: http://msdn.microsoft.com/en-us/library/5ahda31z(v=VS.85).aspx
//WshFSO: http://msdn.microsoft.com/en-us/library/6tkce7xa(v=VS.85).aspx
var WshFSO = new ActiveXObject('Scripting.FileSystemObject');
var WshShell = new ActiveXObject('WScript.Shell');
if(WScript.Arguments.Count() != 1){
	WScript.Echo("Missing parameters: ... <mp3 folder>");
	WScript.Quit();
}

var source_cat = WScript.Arguments.Item(0);
var beat_exe_dir = "c:\\_WPLabs\\_Portable\\SonicAnnot\\";

function processFolder(fromFolder)
{
	if(WshFSO.FileExists(fromFolder)){
		return [WshFSO.GetFile(fromFolder)];
	}
	var f = WshFSO.GetFolder(fromFolder);
	var innerfiles = f.files.count;
	var ff = new Enumerator(f.Files);
	var totallist = [];
	for (; !ff.atEnd(); ff.moveNext()){
		var videof = ff.item();
		var isOk = false;
		if(videof.path.indexOf(".mp3") > 0){
			isOk = true;
		}
		if(isOk){
			totallist.push(videof);
		}
	}
	var fc = new Enumerator(f.SubFolders);
	for (; !fc.atEnd(); fc.moveNext()){
		// For each subfolder
		var innerfiles = processFolder(fc.item());
		totallist = totallist.concat(innerfiles);
	}
	return totallist;
}

var totallist = processFolder(source_cat);
WScript.Echo(source_cat+" files found:\n\n"+totallist.join("\n"));

var handled_ok = 0;
for(var i=0;i<totallist.length;i++){
	var mp3file = totallist[i];
	var beat_cmd = beat_exe_dir + "sonic-annotator.exe -t \"beat-extract.rdf\"  -w json \""+mp3file+"\"";
	WScript.Echo("Grabbing: "+beat_cmd);
	WshShell.Run(beat_cmd,7,true);//1 - normal
	handled_ok++;
}

WScript.Echo("Done! ok:"+handled_ok);
