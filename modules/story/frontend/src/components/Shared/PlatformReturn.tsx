import './PlatformReturn.css'
import { Link, useLocation } from 'react-router-dom'

export default function PlatformReturn() {
  const { pathname } = useLocation()
  // The play screen already owns its full top navigation.  A second fixed
  // platform button covered the in-story back button and title on small widths.
  if (pathname.startsWith('/story-create/play/')) return null
  return (
    <>
      <a className="platform-return" href="http://localhost:4173/?from=story">← 返回探索星球</a>
      {pathname === '/story-create/characters' && (
        <Link className="story-home-return" to="/story-create">⌂ 故事共创首页</Link>
      )}
    </>
  )
}
