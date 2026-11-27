export type TileScene='ground'|'upstairs'|'yard';

const TILE=64;
const px=(n:number)=>Math.round(n);

function tileRect(ctx:CanvasRenderingContext2D,x:number,y:number,w:number,h:number,fill:string,stroke?:string){
 ctx.fillStyle=fill;ctx.fillRect(px(x),px(y),px(w),px(h));
 if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=4;ctx.strokeRect(px(x)+2,px(y)+2,px(w)-4,px(h)-4);}
}
function plankFloor(ctx:CanvasRenderingContext2D,x:number,y:number,w:number,h:number){
 tileRect(ctx,x,y,w,h,'#b97848','#5f3b32');
 ctx.strokeStyle='#8f563c';ctx.lineWidth=2;
 for(let yy=y;yy<y+h;yy+=32){ctx.beginPath();ctx.moveTo(x,yy);ctx.lineTo(x+w,yy);ctx.stroke();}
 for(let yy=y;yy<y+h;yy+=64)for(let xx=x+((yy/64)%2?32:0);xx<x+w;xx+=96){ctx.beginPath();ctx.moveTo(xx,yy);ctx.lineTo(xx,yy+32);ctx.stroke();}
}
function rug(ctx:CanvasRenderingContext2D,x:number,y:number,w:number,h:number,color='#8c6b8f'){
 tileRect(ctx,x,y,w,h,color,'#543e59');tileRect(ctx,x+12,y+12,w-24,h-24,'#c4a4ba','#765574');
}
function wall(ctx:CanvasRenderingContext2D,x:number,y:number,w:number,h:number){
 tileRect(ctx,x,y,w,h,'#d5b7c7','#604751');ctx.fillStyle='#f2dde2';ctx.fillRect(x+7,y+7,w-14,12);
}
function furniture(ctx:CanvasRenderingContext2D,x:number,y:number,w:number,h:number,kind:'bed'|'sofa'|'table'|'shelf'|'counter'){
 const wood='#76503a',edge='#4b342d',cream='#ead8bd';tileRect(ctx,x,y,w,h,wood,edge);
 if(kind==='bed'){tileRect(ctx,x+10,y+10,w-20,h-20,cream,'#8d6b60');tileRect(ctx,x+16,y+16,w-32,42,'#fff0dc');}
 if(kind==='sofa'){tileRect(ctx,x+12,y+14,w-24,h-28,'#b497b1','#614e63');ctx.strokeStyle='#765f79';ctx.beginPath();ctx.moveTo(x+w/2,y+18);ctx.lineTo(x+w/2,y+h-12);ctx.stroke();}
 if(kind==='table'){tileRect(ctx,x+12,y+12,w-24,h-24,'#ba7b4c','#65412f');}
 if(kind==='shelf'){for(let yy=y+18;yy<y+h-12;yy+=34){ctx.fillStyle='#503c31';ctx.fillRect(x+8,yy,w-16,5);for(let xx=x+14;xx<x+w-15;xx+=18){ctx.fillStyle=['#8b6680','#6f8895','#c08a58'][Math.floor(xx/18)%3];ctx.fillRect(xx,yy-18,12,18);}}}
 if(kind==='counter'){tileRect(ctx,x+9,y+9,w-18,h-18,cream,'#76503a');}
}
function stairs(ctx:CanvasRenderingContext2D,x:number,y:number,w:number,h:number){
 tileRect(ctx,x,y,w,h,'#6a4937','#3d2c29');for(let yy=y+12;yy<y+h-8;yy+=18)tileRect(ctx,x+9,yy,w-18,10,'#b47849','#68432f');
}
function drawIndoor(ctx:CanvasRenderingContext2D,scene:TileScene){
 ctx.fillStyle='#261e2a';ctx.fillRect(0,0,1536,1024);
 plankFloor(ctx,80,145,1376,770);
 wall(ctx,80,145,1376,54);wall(ctx,80,861,1376,54);wall(ctx,80,145,54,770);wall(ctx,1402,145,54,770);
 if(scene==='ground'){
  wall(ctx,500,145,34,270);wall(ctx,500,535,34,380);wall(ctx,1000,145,34,225);wall(ctx,1000,520,34,395);
  rug(ctx,600,355,330,255);furniture(ctx,1080,275,305,215,'counter');furniture(ctx,350,335,125,250,'shelf');
  furniture(ctx,1090,605,290,205,'sofa');furniture(ctx,670,420,190,105,'table');stairs(ctx,350,590,150,180);
  tileRect(ctx,680,858,190,48,'#705040','#3e2c28');
 }else{
  wall(ctx,510,145,34,255);wall(ctx,510,545,34,370);wall(ctx,1010,145,34,255);wall(ctx,1010,545,34,370);
  rug(ctx,590,330,350,240,'#8092a6');furniture(ctx,1070,370,290,205,'bed');furniture(ctx,630,625,260,120,'sofa');
  furniture(ctx,1080,665,260,150,'shelf');furniture(ctx,190,290,240,150,'bed');stairs(ctx,315,480,180,175);
 }
}
function grassTile(ctx:CanvasRenderingContext2D,x:number,y:number,variant:number){
 tileRect(ctx,x,y,TILE,TILE,variant%2?'#86b85b':'#8fc160');ctx.fillStyle='#74a74e';
 for(let i=0;i<5;i++){const dx=(i*17+variant*11)%58,dy=(i*29+variant*7)%58;ctx.fillRect(x+dx,y+dy,3,6);}
}
function drawYard(ctx:CanvasRenderingContext2D){
 for(let y=0;y<1024;y+=TILE)for(let x=0;x<1536;x+=TILE)grassTile(ctx,x,y,(x/TILE+y/TILE)%4);
 const path='#d8b57c';for(const [x,y,w,h] of [[700,235,170,730],[0,760,1536,150],[600,690,380,140]])tileRect(ctx,x,y,w,h,path,'#a78358');
 tileRect(ctx,555,10,440,285,'#84513b','#4d342d');tileRect(ctx,585,45,380,210,'#d6b889','#6a4536');
 tileRect(ctx,680,230,190,75,'#a96843','#59382f');
 tileRect(ctx,1055,605,365,245,'#5b9cb3','#376a7b');ctx.fillStyle='#82c5d1';for(let y=625;y<830;y+=30)ctx.fillRect(1070,y,330,4);
 tileRect(ctx,115,515,295,285,'#8c593c','#5f3b2d');for(let y=535;y<790;y+=70)for(let x=135;x<395;x+=78)tileRect(ctx,x,y,58,48,'#70442f','#9f6a45');
 for(const [x,y] of [[40,40],[70,280],[1240,60],[1330,300],[430,30],[1120,160]]){ctx.fillStyle='#47783f';ctx.beginPath();ctx.arc(x+48,y+58,54,0,Math.PI*2);ctx.fill();ctx.fillStyle='#755039';ctx.fillRect(x+41,y+58,16,70);}
}

export function drawTileWorld(ctx:CanvasRenderingContext2D,scene:TileScene){
 ctx.save();ctx.imageSmoothingEnabled=false;if(scene==='yard')drawYard(ctx);else drawIndoor(ctx,scene);ctx.restore();
}
