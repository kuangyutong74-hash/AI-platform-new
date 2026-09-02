import { useEffect, useState } from 'react';
import { getStoryMessages, type StoryMessage } from '../../api/endpoints';
import Loading from '../Shared/Loading';
import { useModalHeaderActions } from '../Shared/Modal';
import PinyinText from '../Story/PinyinText';
import { buildStoryParagraphs } from '../../utils/storyPresentation';
import './StoryReader.css';

interface StoryReaderProps {
  storyId: number;
}

export default function StoryReader({ storyId }: StoryReaderProps) {
  const [messages, setMessages] = useState<StoryMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPinyin, setShowPinyin] = useState(false);
  const [fontSize, setFontSize] = useState<'s' | 'm' | 'l'>('m');
  const setModalHeaderActions = useModalHeaderActions();

  useEffect(() => {
    if (!setModalHeaderActions) return;
    setModalHeaderActions(
      <div className="reader-toolbar">
        <span className="reader-toolbar-label">字号</span>
        <div className="fontsize-toggle">
          <button className={`fs-btn ${fontSize==='s'?'fs-active':''}`} onClick={()=>setFontSize('s')}>小</button>
          <button className={`fs-btn ${fontSize==='m'?'fs-active':''}`} onClick={()=>setFontSize('m')}>中</button>
          <button className={`fs-btn ${fontSize==='l'?'fs-active':''}`} onClick={()=>setFontSize('l')}>大</button>
        </div>
        <span className="reader-toolbar-label">拼音</span>
        <button type="button" className={`reader-pinyin-toggle ${showPinyin?'active':''}`} onClick={()=>setShowPinyin(c=>!c)} aria-pressed={showPinyin}>{showPinyin?'关闭':'开启'}</button>
      </div>
    );
    return () => setModalHeaderActions(null);
  }, [fontSize, setModalHeaderActions, showPinyin]);

  useEffect(() => {
    setLoading(true);
    getStoryMessages(storyId)
      .then(setMessages)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [storyId]);

  if (loading) return <Loading text="加载故事中..." />;
  if (error) return <p className="reader-error">{error}</p>;

  const paragraphs = buildStoryParagraphs(messages);

  return (
    <div className={`story-reader ${showPinyin ? 'story-reader-pinyin' : ''} reader-fs-${fontSize}`}>
      <article className="reader-story-paper" aria-label="完整故事正文">
        {paragraphs.length > 0 ? paragraphs.map((paragraph, index) => (
          <p key={`${index}-${paragraph.slice(0, 12)}`}>
            <PinyinText text={paragraph} enabled={showPinyin} />
          </p>
        )) : <p className="reader-empty">这个故事还没有正文。</p>}
      </article>
    </div>
  );
}
