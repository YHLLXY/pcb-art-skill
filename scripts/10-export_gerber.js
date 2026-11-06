const f=await eda.pcb_ManufactureData.getGerberFile('CQUPT_Gerber');
const ok=await eda.sys_FileSystem.saveFileToFileSystem('C:\\Users\\32447\\AppData\\Local\\Temp\\dsh\\cq.zip', f);
return 'saved '+ok;