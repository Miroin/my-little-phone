import {floorPlan} from './floorPlan';
import {roomMeta,roomOrder,type HomeState,type RoomId} from './model';

export function HomeOverview({state,onEnter}:{state:HomeState;onEnter:(room:RoomId)=>void}){
  const occupants=(room:RoomId)=>[...Object.values(state.members),...Object.values(state.pets)].filter(item=>item.room===room);
  return <main className="home-overview">
    <header className="home-heading"><div><small>OUR LITTLE HOME · {state.environment.mode.toUpperCase()}</small><h1>我们一起生活的家</h1><p>今天 {state.environment.temperature}° · {state.environment.weather==='clear'?'窗外晴朗':'空气安静'}，每个房间都留着正在发生的生活。</p></div><div className="home-status-orb"><i/><span>{new Intl.DateTimeFormat('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date())}</span><small>HOME IS AWAKE</small></div></header>
    <section className="floor-plan" aria-label="大平层房屋总览">
      <div className="plan-corridor"><span>OUR HOME</span><i/><small>生活从这里流向每个房间</small></div>
      {roomOrder.map(room=><button key={room} className={`plan-room plan-${floorPlan[room].grid}`} onClick={()=>onEnter(room)}>
        <span className="room-number">0{roomOrder.indexOf(room)+1}</span><div className={`room-miniature miniature-${room}`} aria-hidden="true"><i/><b/><em/></div>
        <div className="room-copy"><small>{roomMeta[room].english}</small><h2>{roomMeta[room].name}</h2><p>{floorPlan[room].feature}</p></div>
        <div className="room-occupants">{occupants(room).map(item=><span key={item.id} title={item.activity}>{'species' in item?(item.species==='cat'?'猫':'犬'):item.name.slice(0,1)}</span>)}</div>
      </button>)}
    </section>
    <footer className="home-family-strip"><div><small>AT HOME NOW</small><b>沈砚在{roomMeta[state.members.shenyan.room].name}</b><span>{state.members.shenyan.activity}</span></div><div><small>PETS</small><b>{state.pets.abi.name}与{state.pets.bernese.name}</b><span>各自在喜欢的地方待着</span></div></footer>
  </main>;
}
