import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  listCharacters,
  createCharacter,
  deleteCharacter,
  createStory,
  type Character,
} from "../api/endpoints";
import CharacterCard from "../components/Character/CharacterCard";
import CharacterCreator from "../components/Character/CharacterCreator";
import Button from "../components/Shared/Button";
import Loading from "../components/Shared/Loading";
import PngIcon from "../components/Shared/PngIcon";
import { AGE_GROUP_LABELS, useChannel, type AgeGroup } from "../contexts/ChannelContext";
import { AGE_PROFILES } from "../data/ageProfiles";
import { ApiError } from "../api/client";
import "./CharacterPage.css";

type AgeFilter = "all" | AgeGroup;
type PlatformIdentity = { displayName: string; avatarId: string; ageGroup?: AgeGroup; platformOrigin?: string };
const PLATFORM_CORE_URL = import.meta.env.VITE_PLATFORM_CORE_URL || "http://localhost:8020";

function readPlatformIdentity(): PlatformIdentity | null {
  try {
    const launch = window.name ? JSON.parse(window.name) : null;
    const student = launch?.namespace === "ai-bole.launch-context.v1" ? launch.context?.student : null;
    if (student?.displayName) {
      const identity = {
        displayName: student.displayName,
        avatarId: student.avatarId || "student-1",
        platformOrigin: launch.context?.platformOrigin,
      };
      sessionStorage.setItem("ai-bole.story.identity", JSON.stringify(identity));
      return identity;
    }
  } catch { /* a module may use window.name for unrelated state */ }
  try {
    return JSON.parse(sessionStorage.getItem("ai-bole.story.identity") || "null");
  } catch {
    return null;
  }
}

async function resolvePlatformIdentity(): Promise<PlatformIdentity | null> {
  const localIdentity = readPlatformIdentity();
  if (localIdentity) return localIdentity;
  try {
    const response = await fetch(`${PLATFORM_CORE_URL}/api/account/me`, { credentials: "include" });
    if (!response.ok) return null;
    const session = await response.json();
    const subject = session?.selected_student
      ?? (session?.account?.role === "student" ? session.account : null);
    if (!subject?.display_name) return null;
    const identity: PlatformIdentity = {
      displayName: subject.display_name,
      avatarId: subject.avatar_id || "student-1",
      ageGroup: Number(subject.age) <= 7 ? "4-7" : "8-12",
    };
    sessionStorage.setItem("ai-bole.story.identity", JSON.stringify(identity));
    return identity;
  } catch {
    return null;
  }
}

export default function CharacterPage() {
  const { ageGroup: channelAgeGroup } = useChannel();
  const relayPrompt = useMemo(() => new URLSearchParams(window.location.search).get("relayPrompt") || "", []);
  const relayTitle = useMemo(() => new URLSearchParams(window.location.search).get("relayTitle") || "", []);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChar, setSelectedChar] = useState<Character | null>(null);
  const [ageFilter, setAgeFilter] = useState<AgeFilter>("all");
  const [theme, setTheme] = useState(relayPrompt ? "__custom__" : "");
  const [customTheme, setCustomTheme] = useState(relayPrompt);
  const [storyTitle, setStoryTitle] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [identityError, setIdentityError] = useState("");
  const [platformIdentity, setPlatformIdentity] = useState<PlatformIdentity | null>(readPlatformIdentity);
  const navigate = useNavigate();

  useEffect(() => {
    loadCharacters();
  }, []);

  // 选中角色切换时，重置故事主题选择
  useEffect(() => {
    setTheme(relayPrompt ? "__custom__" : "");
    setCustomTheme(relayPrompt);
    setError("");
  }, [selectedChar?.id, relayPrompt]);

  async function loadCharacters() {
    setIdentityError("");
    try {
      const [chars, resolvedIdentity] = await Promise.all([
        listCharacters(),
        resolvePlatformIdentity(),
      ]);
      setCharacters(chars);
      setPlatformIdentity(resolvedIdentity);
      if (resolvedIdentity && channelAgeGroup) {
        const existing = chars.find((char) => char.nickname === resolvedIdentity.displayName && char.avatar_type === resolvedIdentity.avatarId);
        if (existing) setSelectedChar(existing);
        else {
          const created = await createCharacter({nickname:resolvedIdentity.displayName,avatar_type:resolvedIdentity.avatarId,avatar_color:"#f0cb70",personality:"以我自己的方式去探索和创造",age_group:resolvedIdentity.ageGroup || channelAgeGroup});
          setCharacters((previous) => [...previous, created]);
          setSelectedChar(created);
        }
      }
    } catch (err: unknown) {
      if (platformIdentity) {
        setIdentityError(
          err instanceof ApiError && err.status === 401
            ? "登录信息没有跟过来，请返回探索星球后重新进入故事共创。"
            : "暂时没能带入你的形象，请重试。",
        );
      } else {
        setError(err instanceof Error ? err.message : "角色加载失败，请重试");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(data: {
    nickname: string;
    avatar_type: string;
    avatar_color: string;
    personality?: string;
    age_group: AgeGroup;
  }) {
    const newChar = await createCharacter(data);
    setCharacters((prev) => [...prev, newChar]);
    // 创建后自动选中新角色，右侧立刻出现「开始故事」卡片，无需再手动点击
    setSelectedChar(newChar);
    // 若当前筛选的是其他年龄段，切到新角色所属年龄段，保证左侧列表可见
    if (
      ageFilter !== "all" &&
      (newChar.age_group === "4-7" || newChar.age_group === "8-12") &&
      ageFilter !== newChar.age_group
    ) {
      setAgeFilter(newChar.age_group);
    }
  }

  async function handleDelete(character: Character) {
    if (
      !confirm(
        `确定要删除角色"${character.nickname}"吗？相关的故事也会被删除哦！`,
      )
    )
      return;
    await deleteCharacter(character.id);
    setCharacters((prev) => prev.filter((c) => c.id !== character.id));
    if (selectedChar?.id === character.id) {
      setSelectedChar(null);
    }
  }

  async function handleStartStory() {
    if (!selectedChar) return;
    const isCustomTheme = theme === "__custom__";
    if (isCustomTheme && !customTheme.trim()) {
      setError("请填写自定义主题哦~");
      return;
    }
    setStarting(true);
    setError("");
    try {
      const effectiveTheme = isCustomTheme
        ? customTheme.trim()
        : theme || undefined;
      const story = await createStory({
        character_id: selectedChar.id,
        theme: effectiveTheme,
        title: storyTitle.trim() || undefined,
      });
      navigate(`/story-create/play/${story.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "创建故事失败");
    } finally {
      setStarting(false);
    }
  }

  // 选中角色所属年龄段 → 对应主题选项；未标注年龄段时回退到当前通道
  const selectedAgeGroup: AgeGroup | null =
    selectedChar?.age_group === "4-7" || selectedChar?.age_group === "8-12"
      ? (selectedChar.age_group as AgeGroup)
      : channelAgeGroup;
  const themes = useMemo(
    () => (selectedAgeGroup ? AGE_PROFILES[selectedAgeGroup].themes : []),
    [selectedAgeGroup],
  );

  const filteredCharacters = useMemo(() => {
    if (ageFilter === "all") return characters;
    return characters.filter((c) => c.age_group === ageFilter);
  }, [characters, ageFilter]);

  if (loading) return <Loading text="加载角色中..." />;

  if (platformIdentity) return (
    <div className="character-page page unified-story-start">
      <section className="unified-identity-banner">
        <img src={`http://localhost:3000/assets/avatars/student/${platformIdentity.avatarId}.png`} alt="" />
        <div><h2>{platformIdentity.displayName}，今天想创作什么故事？</h2><p>故事会直接使用你在探索星球选好的昵称和形象。</p></div>
      </section>
      {relayPrompt&&<aside className="story-relay-banner"><b>✨ 探索接力：从《{relayTitle||"上一件作品"}》出发</b><span>{relayPrompt}</span></aside>}
      <div className="start-story-card unified-story-card">
        <div className="start-field"><label><PngIcon name="action-write" size={24} /> 故事名字（可选）</label><input type="text" value={storyTitle} onChange={(e)=>setStoryTitle(e.target.value)} placeholder="给你的故事取个名字吧" maxLength={50}/></div>
        <div className="theme-selector"><label>选择故事主题</label><div className="theme-grid">{themes.map((t)=><button key={t.value} className={`theme-option ${theme===t.value?"theme-option-selected":""}`} onClick={()=>setTheme(t.value)}><PngIcon name={t.icon} size={42}/><span>{t.label}</span></button>)}</div>{theme==="__custom__"&&<input type="text" className="custom-theme-input" value={customTheme} onChange={(e)=>setCustomTheme(e.target.value)} placeholder="输入你想创作的故事主题" maxLength={50} autoFocus/>}</div>
        {error&&<p className="start-error" role="alert">{error}</p>}
        {!selectedChar&&!identityError&&<p className="identity-syncing" role="status">正在带入你的形象…</p>}
        {identityError?<div className="identity-sync-error" role="alert"><p>{identityError}</p><div><Button variant="secondary" onClick={loadCharacters}>重试</Button><a className="btn btn-accent btn-md" href={`${platformIdentity.platformOrigin || `http://${window.location.hostname}:4173`}/?from=story-auth-error`}>返回探索星球</a></div></div>:<Button variant="accent" size="lg" onClick={handleStartStory} disabled={starting||!selectedChar}>{starting?"准备中...":"开始创作故事"}</Button>}
      </div>
    </div>
  );

  return (
    <div className="character-page page">
      <div className="character-layout">
        {/* Left: Character list */}
        <div className="character-section">
          <h2 className="section-title"> 我的角色</h2>

          {/* 年龄段筛选 */}
          <div className="age-filter-row">
            <button
              className={`age-filter-btn ${ageFilter === "all" ? "age-filter-btn-active" : ""}`}
              onClick={() => setAgeFilter("all")}
            >
              全部（{characters.length}）
            </button>
            {(["4-7", "8-12"] as const).map((group) => (
              <button
                key={group}
                className={`age-filter-btn age-filter-btn-${group} ${ageFilter === group ? "age-filter-btn-active" : ""}`}
                onClick={() => setAgeFilter(group)}
              >
                {AGE_GROUP_LABELS[group]}
              </button>
            ))}
          </div>

          {filteredCharacters.length === 0 ? (
            <div className="character-empty">
              <PngIcon name="avatar-explorer" size={150} />
              <p>
                {ageFilter === "all" ? (
                  <>
                    还没有角色哦，
                    <br />
                    在右边创建一个吧！
                  </>
                ) : (
                  <>
                    这个年龄段还没有角色哦，
                    <br />
                    在右边创建一个吧！
                  </>
                )}
              </p>
            </div>
          ) : (
            <div className="character-list">
              {filteredCharacters.map((char) => (
                <CharacterCard
                  key={char.id}
                  character={char}
                  selected={selectedChar?.id === char.id}
                  onSelect={setSelectedChar}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right: Creator + Start side by side */}
        <div className="character-section character-section-right">
          <div className="creator-start-row">
            <div className="creator-start-col">
              <CharacterCreator onCreate={handleCreate} />
            </div>
            {selectedChar && (
              <div className="creator-start-col">
                <div className="start-story-card animate-slide-up">
                  <h3 className="section-title"><PngIcon name="theme-space" size={34} /> 开始故事</h3>
                  <p className="start-story-char">
                    角色：<strong>{selectedChar.nickname}</strong>
                  </p>
                  {selectedAgeGroup && (
                    <p className="start-story-channel">
                      {selectedChar.age_group
                        ? `故事主题按「${AGE_GROUP_LABELS[selectedAgeGroup]}」推荐`
                        : `该角色未标注年龄段，按「${AGE_GROUP_LABELS[selectedAgeGroup]}」推荐主题`}
                    </p>
                  )}

                  <div className="start-field">
                    <label><PngIcon name="action-write" size={24} /> 故事名字（可选）</label>
                    <input
                      type="text"
                      value={storyTitle}
                      onChange={(e) => setStoryTitle(e.target.value)}
                      placeholder="给你的故事取个名字吧"
                      maxLength={50}
                    />
                  </div>

                  <div className="theme-selector">
                    <label>选择故事主题</label>
                    <div className="theme-grid">
                      {themes.map((t) => (
                        <button
                          key={t.value}
                          className={`theme-option ${theme === t.value ? "theme-option-selected" : ""}`}
                          onClick={() => setTheme(t.value)}
                        >
                          <PngIcon name={t.icon} size={42} />
                          <span>{t.label}</span>
                        </button>
                      ))}
                    </div>
                    {theme === "__custom__" && (
                      <input
                        type="text"
                        className="custom-theme-input"
                        value={customTheme}
                        onChange={(e) => setCustomTheme(e.target.value)}
                        placeholder="输入你想创作的故事主题，例如：草原上的动物运动会"
                        maxLength={50}
                        autoFocus
                      />
                    )}
                  </div>

                  {error && <p className="start-error">{error}</p>}

                  <Button
                    variant="accent"
                    size="lg"
                    onClick={handleStartStory}
                    disabled={starting}
                  >
                    {starting ? "准备中..." : "开始创作故事"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
