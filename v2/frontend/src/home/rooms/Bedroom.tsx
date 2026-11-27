import type {RoomProps} from '../RoomScene';
import {BedroomArtwork} from '../RoomArtwork';
export function Bedroom({state,onPatch,onOpen}:RoomProps){const room=state.roomStates.bedroom,bedActivity=room.bedActivity||'idle';const useBed=()=>{const next=bedActivity==='idle'?'sitting':bedActivity==='sitting'?'lying':'idle',copy=next==='sitting'?'你在床边坐下，床垫轻轻陷下去':next==='lying'?'你躺进柔软的被子里休息':'你从床边起身，整理好了被角';onPatch({bedActivity:next,note:copy},copy)};return <div className={`interior bedroom-interior ${room.lights?'bedroom-lit':'bedroom-dim'} ${room.curtains?'curtains-closed':'curtains-open'} bed-${bedActivity}`}>
  <img className="bedroom-perspective-art" src="./home-assets/rooms/bedroom-v2/bedroom-perspective.png" alt="" aria-hidden="true"/>
  <BedroomArtwork lightsOn={room.lights} curtainsClosed={Boolean(room.curtains)} bedActivity={bedActivity}/>
  <button className="object-touch touch-photo" aria-label="打开墙上的纪念照片" data-label="纪念照片" onClick={()=>onOpen('memories')}/>
  <button className="object-touch touch-curtain" aria-label={room.curtains?'拉开窗帘':'合上窗帘'} data-label={room.curtains?'拉开窗帘':'合上窗帘'} onClick={()=>onPatch({curtains:!room.curtains,note:room.curtains?'窗帘打开，阳光落在床边':'窗帘合上，卧室更安静了'},'窗帘状态已保存')}/>
  <button className="object-touch touch-lamp" aria-label={room.lights?'关闭床头灯':'打开床头灯'} data-label={room.lights?'关灯':'开灯'} onClick={()=>onPatch({lights:!room.lights,note:room.lights?'床头灯熄灭了':'床头亮起柔和的暖光'},'卧室灯光已更新')}/>
  <button className="object-touch touch-bed" aria-label={bedActivity==='idle'?'坐到床边':bedActivity==='sitting'?'躺到床上':'从床上起身'} data-label={bedActivity==='idle'?'坐到床边':bedActivity==='sitting'?'躺下休息':'起身'} onClick={useBed}/>
  <button className="object-touch touch-book" aria-label="打开床头的日记" data-label="床头日记" onClick={()=>onOpen('journal')}/>
 </div>}
