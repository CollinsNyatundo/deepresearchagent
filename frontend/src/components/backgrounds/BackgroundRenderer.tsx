import React, { Suspense, useMemo } from 'react'
import { useBackground } from '../../hooks/useBackground'

const MoonlitRipple = React.lazy(() => import('./MoonlitRipple'))
const FlowField = React.lazy(() => import('./FlowField'))
const RainOnGlass = React.lazy(() => import('./RainOnGlass'))
const SolidBackground = React.lazy(() => import('./SolidBackground'))

export default function BackgroundRenderer() {
  const { state } = useBackground()

  const background = useMemo(() => {
    switch (state.mode) {
      case 'moonlit':
        return <MoonlitRipple />
      case 'silk':
        return <FlowField />
      case 'rain':
        return <RainOnGlass />
      case 'solid':
      default:
        return <SolidBackground color={state.solidColor} />
    }
  }, [state.mode, state.solidColor])

  return (
    <div className="absolute inset-0 z-0">
      <Suspense fallback={<div className="w-full h-full bg-black" />}>
        {background}
      </Suspense>
    </div>
  )
}
