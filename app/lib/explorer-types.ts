export type ExplorerModule="registration"|"story"|"deep_sea"|"career"|"chat";

export type ExplorerSessionMoment={
  id:string;
  occurredAt:string;
  durationSeconds:number;
  caption:string;
};

export type ExplorerItem={
  id:string;
  module:ExplorerModule;
  kind:string;
  title:string;
  summary:string;
  detail:string;
  highlightReason:string;
  quote:string;
  occurredAt:string;
  status:string;
  unlocked:boolean;
  metricLabel:string;
  metricValue:string;
  usageCount:number;
  firstUsedAt:string;
  lastUsedAt:string;
  durationSeconds:number;
  durationCoverage:number;
  evidenceCount:number;
  artifactCount:number;
  observations:string[];
  recentSessions:ExplorerSessionMoment[];
  island:string;
  collection:string;
  scene:string;
  milestoneImage:string;
  tone:string;
  isHighlight:boolean;
  snapshotUrl:string;
  comments:Array<{id:string;body:string;authorName:string;authorKind:string;createdAt:string}>;
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
