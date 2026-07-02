import { Routes, Route } from 'react-router-dom'

import Home from '@/pages/Home'
import Settings from '@/pages/Settings'

const items = [{ slug: 'a' }, { slug: 'b' }]

export default function Router() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/settings" element={<Settings />} />
      {items.map((x) => (
        <Route key={x.slug} path={`/dyn/${x.slug}`} element={<Home />} />
      ))}
    </Routes>
  )
}
