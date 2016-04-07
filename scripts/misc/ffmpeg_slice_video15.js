// cscript "c:\_WPLabs\PROJECTS_GAMES\Github-kristallum\scripts\misc\ffmpeg_slice_video15.js" "d:\_Video\Starship Operators" "f:\_ZRips"



//WScript: http://msdn.microsoft.com/en-us/library/5ahda31z(v=VS.85).aspx
//WshFSO: http://msdn.microsoft.com/en-us/library/6tkce7xa(v=VS.85).aspx
var WshFSO = new ActiveXObject('Scripting.FileSystemObject');
var WshShell = new ActiveXObject('WScript.Shell');
if(WScript.Arguments.Count() != 2){
	WScript.Echo("Missing parameters: ... <video files> <output folder>");
	WScript.Quit();
}

//var target_cat = WshFSO.GetParentFolderName(WScript.ScriptFullName)
var source_cat = WScript.Arguments.Item(0);
var target_cat = WScript.Arguments.Item(1);
var ffmpeg_exe = "c:\\_WPLabs\\_Portable\\ffmpeg\\ffmpeg.exe";

if(!WshFSO.FolderExists(target_cat)){
	if(!WshFSO.CreateFolder(target_cat)){
		WScript.Echo("Can`t create output folder: "+target_cat);
		WScript.Quit();
	}
}

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
		var isVideo = false;
		if(videof.path.indexOf(".mp4") > 0){
			isVideo = true;
		}
		if(videof.path.indexOf(".avi") > 0){
			isVideo = true;
		}
		if(videof.path.indexOf(".mkv") > 0){
			isVideo = true;
		}
		if(isVideo){
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

var extendedWhitespaceCharsList = [".","&","%","+",",","?","!",":","-",";","'"," ","  ","  ","  "];
var extendedIgnoredCharsList = ["\t","{","}","(",")","[","]","\"","<",">","__","___"];
function normalizeLinr(raw_text) {
	for(var i=0;i<extendedWhitespaceCharsList.length;i++){
		raw_text = raw_text.split(extendedWhitespaceCharsList[i]).join("_");
	}
	for(var i=0;i<extendedIgnoredCharsList.length;i++){
		//raw_text = raw_text.replace(extendedIgnoredCharsList[i],"");
		raw_text = raw_text.split(extendedIgnoredCharsList[i]).join("");
	}
	if(raw_text.length == 0){
		return raw_text;
	}
	return raw_text.toLowerCase();
}

var totallist = processFolder(source_cat);
WScript.Echo(source_cat+" files found:\n\n"+totallist.join("\n"));

var handled_ok = 0;
var handled_fail = 0;
for(var i=0;i<totallist.length;i++){
	var videof = totallist[i];
	var videof_cats = WshFSO.GetParentFolderName(videof).split("\\");
	var output_cat = target_cat + "\\" + videof_cats[videof_cats.length-1];
	var output_filepref = normalizeLinr(WshFSO.GetFileName(videof));
	if(output_filepref.length == 0){
		handled_fail++;
		continue;
	}
	//WScript.Echo("Grabbing: "+WshFSO.GetFileName(videof)+" into "+output_cat+" "+output_filepref);
	if(!WshFSO.FolderExists(output_cat)){
		WshFSO.CreateFolder(output_cat);
	}
	// http://stackoverflow.com/questions/19848511/make-thumbs-from-videos-with-ffmpeg-and-php
	var ffmpeg_cmd = ffmpeg_exe + " -i \""+videof.path+"\" -sn -vf \"select='isnan(prev_selected_t)+gte(t-prev_selected_t,15)', setpts=N/(25*TB)\" -qscale:v 2 \""+output_cat+"\\"+output_filepref+"_%03d.jpg\"";
	WScript.Echo("Grabbing: "+ffmpeg_cmd);
	//WScript.Echo(ffmpeg_cmd);
	WshShell.Run(ffmpeg_cmd,7,true);//1 - normal
	//var crunching = WshShell.Exec(ffmpeg_cmd)
	//while(crunching.status == 0){
	//	WScript.Sleep(1000);
	//	//WScript.Echo("inprogres: "+crunching.ExitCode+", "+crunching.status);
	//}
	handled_ok++;
}

WScript.Echo("Done! ok:"+handled_ok+"; fail:"+handled_fail);
