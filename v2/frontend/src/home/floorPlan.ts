import type {RoomId} from './model';
export const floorPlan:Record<RoomId,{grid:string;feature:string}>={
  living:{grid:'living',feature:'壁炉与落地窗'},kitchen:{grid:'kitchen',feature:'开放式岛台'},bedroom:{grid:'bedroom',feature:'柔软的双人床'},study:{grid:'study',feature:'整面书墙'},dressing:{grid:'dressing',feature:'全身镜与衣柜'},balcony:{grid:'balcony',feature:'城市花园'},
};
