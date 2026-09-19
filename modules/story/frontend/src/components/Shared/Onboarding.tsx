import { useState } from 'react';
import Button from './Button';
import PngIcon, { type StoryPngIconName } from './PngIcon';
import './Onboarding.css';

interface Step {
  icon: StoryPngIconName;
  title: string;
  desc: string;
}

const STEPS: Step[] = [
  {
    icon: 'child-explorer',
    title: '欢迎来到故事共创',
    desc: '你来决定角色怎么做，故事导演接着往下讲。每一个选择，都会让故事变得不一样。',
  },
  {
    icon: 'theme-hero',
    title: '选一个故事主题',
    desc: '我们会带入你在探索星球使用的昵称和形象。你只要选择喜欢的主题，也可以给故事取个名字。',
  },
  {
    icon: 'story-director',
    title: '说出你的想法',
    desc: '故事导演每讲一段，就会请你决定接下来发生什么。你可以打字，也可以点麦克风说出来；需要时还能显示拼音、放大文字或朗读故事。',
  },
  {
    icon: 'action-write',
    title: '为故事写下结局',
    desc: '创作几轮后，你可以自己写结局，也可以请故事导演完成。写好的故事会收藏到故事书架和「我的作品」。',
  },
  {
    icon: 'talent-brain',
    title: '回看你的闪光点',
    desc: '故事完成后，可以阅读完整故事，看看自己的精彩表达、创作亮点和下一步小建议。',
  },
  {
    icon: 'theme-space',
    title: '准备好了吗？',
    desc: '点击「开始创作」，选一个主题，让你的故事从第一个选择开始。',
  },
];

interface OnboardingProps {
  onFinish: () => void;
}

export default function Onboarding({ onFinish }: OnboardingProps) {
  const [step, setStep] = useState(0);
  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card animate-pop-in">
        <div className="onboarding-progress">
          {STEPS.map((_, i) => (
            <span key={i} className={`onboarding-dot ${i === step ? 'active' : i < step ? 'done' : ''}`} />
          ))}
        </div>

        <span className="onboarding-emoji"><PngIcon name={current.icon} size={96} /></span>
        <h2 className="onboarding-title">{current.title}</h2>
        <p className="onboarding-desc">{current.desc}</p>

        <div className="onboarding-actions">
          {step > 0 && (
            <Button variant="ghost" size="sm" onClick={() => setStep(step - 1)}>
              ← 上一步
            </Button>
          )}
          <Button variant="primary" size="lg" onClick={() => isLast ? onFinish() : setStep(step + 1)}>
            {isLast ? '开始创作' : '下一步 →'}
          </Button>
        </div>

        {!isLast && (
          <button className="onboarding-skip" onClick={onFinish}>
            跳过引导，直接开始
          </button>
        )}
      </div>
    </div>
  );
}
