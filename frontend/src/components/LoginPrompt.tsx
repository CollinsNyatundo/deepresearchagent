import { AuthModal } from './Auth/AuthModal'
import authBg from '../assets/auth_bg.png'

export default function LoginPrompt() {
  return (
    <div 
      className="h-screen w-full relative overflow-hidden flex items-center justify-center px-4 bg-black bg-cover bg-center select-none"
      style={{ backgroundImage: `url(${authBg})` }}
    >
      {/* Soft gold backdrop glow behind the glass modal for depth */}
      <div className="absolute w-[400px] h-[400px] rounded-full bg-[#c8956c]/5 blur-[120px] pointer-events-none" />

      <AuthModal opened={true} />
    </div>
  )
}
