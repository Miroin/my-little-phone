export type RoomId='living'|'kitchen'|'bedroom'|'study'|'dressing'|'balcony';
export type HomeModule='chat'|'memories'|'journal'|'music'|'cinema'|'schedule'|'profile';
export type HomeTheme='moon-cream';

export type MemberInteraction='idle'|'hug'|'kiss'|'hold-hands'|'sit-together';
export type PetRestState='awake'|'resting'|'sleeping'|'playing';
export interface HomeMember{id:'chenyu'|'shenyan';name:string;room:RoomId;activity:string;mood:string;outfit:string;interactionState:MemberInteraction;lastActiveAt:string;updatedAt:string}
export interface HomePet{id:'abi'|'bernese';name:string;species:'cat'|'dog';room:RoomId;activity:string;mood:number;energy:number;hunger:number;thirst:number;restState:PetRestState;lastActiveAt:string;updatedAt:string}
export interface RoomState{lights:boolean;curtains?:boolean;bedActivity?:'idle'|'sitting'|'lying';accent:string;note:string;updatedAt:string}
export interface LifeEvent{id:string;type:string;room:RoomId;text:string;createdAt:string}
export type MealStatus='idle'|'preparing'|'ready'|'served';
export interface KitchenState{ingredients:Record<string,number>;mealStatus:MealStatus;currentDish:string;preparedBy:'shenyan'|'together'|null;updatedAt:string}
export interface GardenState{plots:Array<{id:string;plant:string;stage:0|1|2|3;watered:boolean}>;lastTendedAt:string}
export interface WardrobeState{activeMember:'chenyu'|'shenyan';outfits:Record<'chenyu'|'shenyan',string[]>;hairstyles:Record<'chenyu'|'shenyan',string[]>;selected:Record<'chenyu'|'shenyan',{outfit:string;hairstyle:string}>}
export interface HomeState{
  schemaVersion:4;
  currentRoom:RoomId|null;
  floorPlan:RoomId[];
  roomStates:Record<RoomId,RoomState>;
  members:Record<HomeMember['id'],HomeMember>;
  pets:Record<HomePet['id'],HomePet>;
  theme:HomeTheme;
  furniture:Record<RoomId,string[]>;
  environment:{mode:'day'|'evening'|'night';weather:'clear'|'cloudy'|'rain';temperature:number;locationName:string;source:'simulated'|'live';updatedAt:string};
  kitchen:KitchenState;
  garden:GardenState;
  wardrobe:WardrobeState;
  lifeEvents:LifeEvent[];
  lastUpdatedAt:string;
  legacyBackup?:unknown;
}

export const roomOrder:RoomId[]=['living','kitchen','bedroom','study','dressing','balcony'];
export const roomMeta:Record<RoomId,{name:string;english:string;hint:string}>={
  living:{name:'客厅',english:'LIVING ROOM',hint:'一起休息、听歌和看电影'},
  kitchen:{name:'厨房与餐厅',english:'KITCHEN & DINING',hint:'准备今晚的饭和咖啡'},
  bedroom:{name:'卧室',english:'BEDROOM',hint:'安静休息与收藏纪念'},
  study:{name:'书房',english:'STUDY',hint:'阅读、写日记和工作'},
  dressing:{name:'衣帽间',english:'DRESSING ROOM',hint:'整理衣物和保存穿搭'},
  balcony:{name:'阳台与花园',english:'BALCONY GARDEN',hint:'看看天气，陪宠物晒太阳'},
};

const now=()=>new Date().toISOString();
const roomState=(note:string):RoomState=>({lights:true,curtains:true,bedActivity:'idle',accent:'cream',note,updatedAt:now()});
export function createDefaultHome():HomeState{return{
  schemaVersion:4,currentRoom:null,floorPlan:roomOrder,
  roomStates:{living:roomState('壁炉旁留着两个人的位置'),kitchen:roomState('晚餐还没有决定'),bedroom:roomState('窗帘透进柔和的光'),study:roomState('书桌上放着未读完的书'),dressing:roomState('今天还没有选择穿搭'),balcony:roomState('植物今天状态很好')},
  members:{chenyu:{id:'chenyu',name:'陈钰',room:'bedroom',activity:'在卧室放松',mood:'安静',outfit:'奶油白家居服',interactionState:'idle',lastActiveAt:now(),updatedAt:now()},shenyan:{id:'shenyan',name:'沈砚',room:'bedroom',activity:'靠在床边休息',mood:'放松',outfit:'深灰色家居服',interactionState:'idle',lastActiveAt:now(),updatedAt:now()}},
  pets:{abi:{id:'abi',name:'阿比',species:'cat',room:'living',activity:'窝在沙发边舔毛',mood:82,energy:68,hunger:24,thirst:18,restState:'resting',lastActiveAt:now(),updatedAt:now()},bernese:{id:'bernese',name:'伯恩山',species:'dog',room:'living',activity:'趴在茶几旁摇尾巴',mood:91,energy:76,hunger:20,thirst:22,restState:'awake',lastActiveAt:now(),updatedAt:now()}},
  theme:'moon-cream',
  furniture:{living:['sofa','coffee-table','fireplace','record-player'],kitchen:['island','dining-table','coffee-machine'],bedroom:['double-bed','nightstands'],study:['desk','bookshelf','reading-chair'],dressing:['wardrobe','mirror','shoe-cabinet'],balcony:['garden-seat','round-table','planters']},
  environment:{mode:'day',weather:'clear',temperature:23,locationName:'未设置城市',source:'simulated',updatedAt:now()},
  kitchen:{ingredients:{蔬菜:4,鸡蛋:6,肉类:3,米面:5,水果:4},mealStatus:'ready',currentDish:'奶油蘑菇烩饭',preparedBy:'shenyan',updatedAt:now()},
  garden:{plots:[{id:'lavender',plant:'薰衣草',stage:2,watered:false},{id:'tomato',plant:'小番茄',stage:1,watered:false},{id:'herb',plant:'香草',stage:3,watered:true}],lastTendedAt:now()},
  wardrobe:{activeMember:'chenyu',outfits:{chenyu:['奶油白家居服','淡紫针织套装','月光约会裙'],shenyan:['深灰色家居服','黑色针织套装','白衬衫约会装']},hairstyles:{chenyu:['柔顺长卷发','低马尾','慵懒盘发'],shenyan:['蓬松碎发','自然侧分','轻短发']},selected:{chenyu:{outfit:'奶油白家居服',hairstyle:'柔顺长卷发'},shenyan:{outfit:'深灰色家居服',hairstyle:'蓬松碎发'}}},
  lifeEvents:[],lastUpdatedAt:now()
};}

export function migrateHomeState(raw:unknown):HomeState{
  if(raw&&typeof raw==='object'&&'schemaVersion' in raw&&Number((raw as any).schemaVersion)>=2){const base=createDefaultHome(),saved=raw as Partial<HomeState>,oldVersion=Number((raw as any).schemaVersion);return{...base,...saved,roomStates:{...base.roomStates,...saved.roomStates},members:{chenyu:{...base.members.chenyu,...saved.members?.chenyu},shenyan:{...base.members.shenyan,...saved.members?.shenyan,...(oldVersion<3?{room:'bedroom' as RoomId,activity:'靠在床边休息'}:{})}},pets:{abi:{...base.pets.abi,...saved.pets?.abi,...(oldVersion<3?{room:'living' as RoomId,activity:'窝在沙发边舔毛'}:{})},bernese:{...base.pets.bernese,...saved.pets?.bernese,...(oldVersion<3?{room:'living' as RoomId,activity:'趴在茶几旁摇尾巴'}:{})}},furniture:{...base.furniture,...saved.furniture},kitchen:{...base.kitchen,...saved.kitchen,ingredients:{...base.kitchen.ingredients,...saved.kitchen?.ingredients}},garden:{...base.garden,...saved.garden},wardrobe:{...base.wardrobe,...saved.wardrobe,selected:{...base.wardrobe.selected,...saved.wardrobe?.selected}},schemaVersion:4};}
  const home=createDefaultHome(),legacy=raw as any;
  home.legacyBackup=raw??undefined;
  const names=legacy?.pet_names;
  if(names?.cat)home.pets.abi.name=String(names.cat).slice(0,24);
  if(names?.dog)home.pets.bernese.name=String(names.dog).slice(0,24);
  const oldPets=legacy?.furniture?.pets;
  if(Array.isArray(oldPets)){const cat=oldPets.find((pet:any)=>pet.kind==='cat'),dog=oldPets.find((pet:any)=>pet.kind==='dog');if(cat){home.pets.abi.mood=Number(cat.mood)||home.pets.abi.mood;home.pets.abi.energy=Number(cat.energy)||home.pets.abi.energy;}if(dog){home.pets.bernese.mood=Number(dog.mood)||home.pets.bernese.mood;home.pets.bernese.energy=Number(dog.energy)||home.pets.bernese.energy;}}
  return home;
}
