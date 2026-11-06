const b=await eda.dmt_Board.getAllBoardsInfo();
const t=b.find(x=>x.name==='Board1')||b[0];
await eda.dmt_EditorControl.openDocument(t.pcb.uuid);
await new Promise(r=>setTimeout(r,2000));
return 'opened '+t.name;