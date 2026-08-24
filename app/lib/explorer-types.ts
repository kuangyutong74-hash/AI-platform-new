export type ExplorerModule="registration"|"story"|"deep_sea"|"career"|"chat";

export type ExplorerItem={
  id:string;
  module:ExplorerModule;
  kind:string;
  title:string;
  summary:string;
  detail:string;
  quote:string;
  occurredAt:string;
  status:string;
  unlocked:boolean;
  metricLabel:string;
  metricValue:string;
  usageCount:number;
  firstUsedAt:string;
  lastUsedAt:string;
  island:string;
  collection:string;
  scene:string;
  milestoneImage:string;
  tone:string;
};

export type ExplorerCollection={
  account:{displayName:string;age:number;createdAt:string};
  works:ExplorerItem[];
  milestones:ExplorerItem[];
  isDemo:boolean;
  worksAreDemo:boolean;
  timelineIsDemo:boolean;
  worksNotice:string;
  timelineNotice:string;
  notice:string;
};
