export type ExplorerModule="registration"|"story"|"deep_sea"|"career"|"chat";

export type ExplorerSessionMoment={
  id:string;
  module?:Exclude<ExplorerModule,"registration">;
  occurredAt:string;
  durationSeconds:number;
  caption:string;
  evidenceCount?:number;
  artifactCount?:number;
  observations?:string[];
};

export type ExplorerGrowthSignal={
  key:string;
  label:string;
  evidenceCount:number;
  moduleCount:number;
  modules:Array<Exclude<ExplorerModule,"registration">>;
  firstSeenAt:string;
  lastSeenAt:string;
  observation:string;
  status:string;
};

export type ExplorerGrowthOverview={
  sessions:ExplorerSessionMoment[];
  todaySessions:ExplorerSessionMoment[];
  todayCompletedCount:number;
  todayDurationSeconds:number;
  todayEvidenceCount:number;
  todayModules:Array<Exclude<ExplorerModule,"registration">>;
  totalCompletedCount:number;
  totalDurationSeconds:number;
  activeDays:number;
  exploredModuleCount:number;
  firstCompletedAt:string;
  lastCompletedAt:string;
  longTermSignals:ExplorerGrowthSignal[];
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
  sourceResourceId:string;
  sourceSessionId:string;
  comments:Array<{id:string;body:string;authorName:string;authorKind:string;createdAt:string}>;
};

export type ExplorerCollection={
  account:{displayName:string;age:number;createdAt:string};
  works:ExplorerItem[];
  milestones:ExplorerItem[];
  growthOverview:ExplorerGrowthOverview;
  isDemo:boolean;
  worksAreDemo:boolean;
  timelineIsDemo:boolean;
  worksNotice:string;
  timelineNotice:string;
  notice:string;
};
