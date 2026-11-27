import type {HomeState,RoomId} from '../model';

const memberSchedule=(hour:number):{room:RoomId;activity:string}=>{
  if(hour<8)return{room:'bedroom',activity:'还在安静休息'};
  if(hour<11)return{room:'kitchen',activity:'在厨房准备早餐'};
  if(hour<15)return{room:'study',activity:'在书房阅读和工作'};
  if(hour<18)return{room:'bedroom',activity:'回卧室休息一会儿'};
  if(hour<21)return{room:'living',activity:'在客厅听唱片'};
  return{room:'bedroom',activity:'靠在床边等你'};
};
const petSchedule=(hour:number)=>hour<8?{room:'bedroom' as RoomId,cat:'蜷在床边睡觉',dog:'趴在卧室门边'}:hour<19?{room:'living' as RoomId,cat:'窝在沙发边舔毛',dog:'趴在茶几旁摇尾巴'}:{room:'living' as RoomId,cat:'在落地灯下伸懒腰',dog:'安静等着一起休息'};

export function advanceOfflineLife(state:HomeState,forceUpgrade=false):HomeState{
  const last=Date.parse(state.members.shenyan.lastActiveAt||state.lastUpdatedAt),elapsed=Date.now()-last;
  if(!forceUpgrade&&Number.isFinite(elapsed)&&elapsed<30*60*1000)return state;
  const hour=new Date().getHours(),stamp=new Date().toISOString(),mealTime=(hour>=7&&hour<=10)||(hour>=17&&hour<=20),madeMeal=mealTime&&state.kitchen.mealStatus==='idle'&&elapsed>3*60*60*1000,shen=madeMeal?{room:'kitchen' as RoomId,activity:'在厨房为你准备好了饭菜'}:memberSchedule(hour),pets=petSchedule(hour);
  const gardenElapsed=Date.now()-Date.parse(state.garden.lastTendedAt),plots=gardenElapsed>6*60*60*1000?state.garden.plots.map(plot=>({...plot,stage:Math.min(3,plot.stage+1) as 0|1|2|3,watered:false})):state.garden.plots;
  return{...state,kitchen:madeMeal?{...state.kitchen,mealStatus:'ready',currentDish:hour<12?'鸡蛋奶香吐司':'奶油蘑菇烩饭',preparedBy:'shenyan',updatedAt:stamp}:state.kitchen,garden:{...state.garden,plots,lastTendedAt:gardenElapsed>6*60*60*1000?stamp:state.garden.lastTendedAt},members:{...state.members,shenyan:{...state.members.shenyan,...shen,interactionState:'idle',lastActiveAt:stamp,updatedAt:stamp}},pets:{abi:{...state.pets.abi,room:pets.room,activity:pets.cat,restState:'resting',lastActiveAt:stamp,updatedAt:stamp},bernese:{...state.pets.bernese,room:pets.room,activity:pets.dog,restState:'awake',lastActiveAt:stamp,updatedAt:stamp}},lastUpdatedAt:stamp};
}
