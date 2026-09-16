import { Navigate, Route, Routes } from 'react-router-dom'
import { ChannelProvider } from './contexts/ChannelContext'
import { StoryProvider } from './contexts/StoryContext'
import Background from './components/Layout/Background'
import CharacterPage from './pages/CharacterPage'
import GalleryPage from './pages/GalleryPage'
import HomePage from './pages/HomePage'
import StoryPlayPage from './pages/StoryPlayPage'
import TalentPage from './pages/TalentPage'
import PlatformReturn from './components/Shared/PlatformReturn'

const STORY_ROOT = '/story-create'

function StoryRoutes() {
  return (
    <Routes>
      <Route index element={<HomePage />} />
      <Route path="characters" element={<CharacterPage />} />
      <Route
        path="play/:storyId"
        element={
          <StoryProvider>
            <StoryPlayPage />
          </StoryProvider>
        }
      />
      <Route path="gallery" element={<GalleryPage />} />
      <Route path="talent/:storyId" element={<TalentPage />} />
      <Route path="*" element={<Navigate to={STORY_ROOT} replace />} />
    </Routes>
  )
}

export default function StoryCreateApp() {
  return (
    <ChannelProvider>
      <Background />
      <PlatformReturn />
      <StoryRoutes />
    </ChannelProvider>
  )
}
