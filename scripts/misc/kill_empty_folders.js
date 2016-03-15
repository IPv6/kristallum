//WScript: http://msdn.microsoft.com/en-us/library/5ahda31z(v=VS.85).aspx
//WshFSO: http://msdn.microsoft.com/en-us/library/6tkce7xa(v=VS.85).aspx
var WshFSO = new ActiveXObject('Scripting.FileSystemObject');
var target_cat = WshFSO.GetParentFolderName(WScript.ScriptFullName)
if(WScript.Arguments.Count() > 0){
	target_cat = WScript.Arguments.Item(0);
}

var debug_action = false;
var total_done = 0;

//WshFSO.MoveFile(filePath,filePath.parentFolder+"\\"+filePathNoParents+markar+"."+ext);
function processFolder(fromFolder)
{
	var f = WshFSO.GetFolder(fromFolder);
	var innerfiles = f.files.count;
	var fc = new Enumerator(f.SubFolders);
	for (; !fc.atEnd(); fc.moveNext()){
		// For each subfolder
		innerfiles += processFolder(fc.item());
	}
	if(innerfiles==0){
		//WScript.Echo("Folder "+fromFolder+" empty");
		WshFSO.DeleteFolder(fromFolder);
		total_done++;
	}else{
		//WScript.Echo("Folder "+fromFolder+" files="+innerfiles);
	}
	return innerfiles;
}

processFolder(target_cat);
WScript.Echo(target_cat+"\n"+"total_done="+total_done);