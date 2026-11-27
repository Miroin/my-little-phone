import {loadHomeState,saveHomeState} from '../api';
import {createDefaultHome,migrateHomeState,type HomeState} from './model';
import {advanceOfflineLife} from './systems/schedule';

const STORAGE_KEY='mlp_interactive_home_v2';
const LEGACY_KEYS=['mlp_home_game_v7','mlp_home_game_v6','mlp_home_game_v5','mlp_home_game_v4'];

export async function loadInteractiveHome():Promise<HomeState>{
  const local=localStorage.getItem(STORAGE_KEY);
  if(local)try{const raw=JSON.parse(local),migrated=advanceOfflineLife(migrateHomeState(raw),Number(raw?.schemaVersion||0)<3);localStorage.setItem(STORAGE_KEY,JSON.stringify(migrated));return migrated;}catch{}
  try{const remote=await loadHomeState();if(remote){const migrated=advanceOfflineLife(migrateHomeState(remote),Number((remote as any)?.schemaVersion||0)<3);localStorage.setItem(STORAGE_KEY,JSON.stringify(migrated));return migrated;}}catch{}
  for(const key of LEGACY_KEYS){const value=localStorage.getItem(key);if(value)try{const migrated=advanceOfflineLife(migrateHomeState(JSON.parse(value)),true);localStorage.setItem(`${STORAGE_KEY}_legacy_backup`,value);localStorage.setItem(STORAGE_KEY,JSON.stringify(migrated));return migrated;}catch{}}
  return createDefaultHome();
}

export async function persistInteractiveHome(state:HomeState):Promise<HomeState>{
  const next={...state,lastUpdatedAt:new Date().toISOString()};
  localStorage.setItem(STORAGE_KEY,JSON.stringify(next));
  try{await saveHomeState(next);}catch{}
  return next;
}
