interface Props {
  color: string
}

export default function SolidBackground({ color }: Props) {
  return (
    <div
      className="w-full h-full"
      style={{ backgroundColor: color }}
    />
  )
}
