import { useEffect, useRef } from 'react'

export default function MoonlitRipple() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const gl = canvas.getContext('webgl', { alpha: false, antialias: false })
    if (!gl) return

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
      gl.viewport(0, 0, canvas.width, canvas.height)
    }
    resize()
    window.addEventListener('resize', resize)

    // Vertex shader
    const vsSource = `
      attribute vec2 a_position;
      void main() {
        gl_Position = vec4(a_position, 0.0, 1.0);
      }
    `

    // Fragment shader — Moonlit Ripple with 7-layer wave simulation
    const fsSource = `
      precision highp float;
      uniform float u_time;
      uniform vec2 u_resolution;
      uniform vec2 u_mouse;

      #define PI 3.14159265359

      // Simplex noise helpers
      vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
      vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
      vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

      float snoise(vec2 v) {
        const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                           -0.577350269189626, 0.024390243902439);
        vec2 i  = floor(v + dot(v, C.yy));
        vec2 x0 = v -   i + dot(i, C.xx);
        vec2 i1;
        i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
        vec4 x12 = x0.xyxy + C.xxzz;
        x12.xy -= i1;
        i = mod289(i);
        vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                                 + i.x + vec3(0.0, i1.x, 1.0));
        vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
        m = m*m;
        m = m*m;
        vec3 x = 2.0 * fract(p * C.www) - 1.0;
        vec3 h = abs(x) - 0.5;
        vec3 ox = floor(x + 0.5);
        vec3 a0 = x - ox;
        m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
        vec3 g;
        g.x  = a0.x  * x0.x  + h.x  * x0.y;
        g.yz = a0.yz * x12.xz + h.yz * x12.yw;
        return 130.0 * dot(m, g);
      }

      // Fractional Brownian Motion
      float fbm(vec2 p) {
        float value = 0.0;
        float amplitude = 0.5;
        float frequency = 1.0;
        for (int i = 0; i < 7; i++) {
          value += amplitude * snoise(p * frequency);
          amplitude *= 0.5;
          frequency *= 2.0;
        }
        return value;
      }

      // Moon disc with craters
      float moon(vec2 uv, vec2 center, float radius) {
        float d = length(uv - center);
        float disc = smoothstep(radius, radius - 0.01, d);
        // Craters
        float crater1 = smoothstep(radius * 0.15, radius * 0.14, length(uv - center - vec2(radius * 0.2, radius * 0.1)));
        float crater2 = smoothstep(radius * 0.1, radius * 0.09, length(uv - center + vec2(radius * 0.15, -radius * 0.05)));
        float crater3 = smoothstep(radius * 0.08, radius * 0.07, length(uv - center - vec2(-radius * 0.05, radius * 0.2)));
        float craters = crater1 * 0.3 + crater2 * 0.25 + crater3 * 0.2;
        return disc * (1.0 - craters * 0.5);
      }

      void main() {
        vec2 uv = gl_FragCoord.xy / u_resolution;
        vec2 aspect = vec2(u_resolution.x / u_resolution.y, 1.0);
        vec2 p = uv * aspect;

        // Moon position
        vec2 moonCenter = vec2(0.75, 0.7);
        float moonRadius = 0.15;

        // Moon color
        float moonMask = moon(p, moonCenter, moonRadius);
        vec3 moonColor = vec3(0.92, 0.9, 0.85) * moonMask;

        // Moonlight glow
        float glow = exp(-length(p - moonCenter) * 3.0) * 0.15;
        vec3 moonGlow = vec3(0.92, 0.9, 0.85) * glow;

        // Water ripples (7 layers)
        float t = u_time * 0.3;
        float ripple = 0.0;
        for (int i = 0; i < 7; i++) {
          float fi = float(i);
          vec2 rp = p + vec2(
            sin(t * 0.5 + fi * 1.3) * 0.02,
            cos(t * 0.7 + fi * 0.9) * 0.02
          );
          float wave = fbm(rp * (2.0 + fi * 0.5) + t * vec2(0.1, 0.15) * (fi + 1.0));
          ripple += wave * (0.5 / (fi + 1.0));
        }
        ripple = ripple * 0.15 + 0.5;

        // Moon reflection on water
        float reflectionY = 0.3;
        float reflectionDist = abs(p.y - reflectionY);
        float reflection = exp(-reflectionDist * 8.0) * smoothstep(0.0, 0.4, p.y);
        reflection *= (1.0 + ripple * 0.5);

        // Mouse interaction (ripple source)
        vec2 mouseNorm = u_mouse / u_resolution;
        float mouseDist = length(p - mouseNorm * aspect);
        float mouseRipple = sin(mouseDist * 30.0 - u_time * 3.0) * exp(-mouseDist * 5.0) * 0.1;
        ripple += mouseRipple;

        // Base water color
        vec3 waterColor = vec3(0.02, 0.03, 0.05) + ripple * vec3(0.03, 0.04, 0.06);

        // Combine
        vec3 color = waterColor + moonGlow;
        color += moonColor * 0.5;
        color += vec3(0.92, 0.9, 0.85) * reflection * 0.4;

        // Desaturate to grayscale at 70% luminance
        float gray = dot(color, vec3(0.299, 0.587, 0.114));
        color = mix(vec3(gray), color, 0.3) * 0.7;

        gl_FragColor = vec4(color, 1.0);
      }
    `

    // Compile shaders
    function compileShader(gl: WebGLRenderingContext, source: string, type: number) {
      const shader = gl.createShader(type)!
      gl.shaderSource(shader, source)
      gl.compileShader(shader)
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error('Shader compile error:', gl.getShaderInfoLog(shader))
        gl.deleteShader(shader)
        return null
      }
      return shader
    }

    const vs = compileShader(gl, vsSource, gl.VERTEX_SHADER)
    const fs = compileShader(gl, fsSource, gl.FRAGMENT_SHADER)
    if (!vs || !fs) return

    const program = gl.createProgram()!
    gl.attachShader(program, vs)
    gl.attachShader(program, fs)
    gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(program))
      return
    }
    gl.useProgram(program)

    // Full-screen quad
    const positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1])
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW)

    const aPosition = gl.getAttribLocation(program, 'a_position')
    gl.enableVertexAttribArray(aPosition)
    gl.vertexAttribPointer(aPosition, 2, gl.FLOAT, false, 0, 0)

    const uTime = gl.getUniformLocation(program, 'u_time')
    const uResolution = gl.getUniformLocation(program, 'u_resolution')
    const uMouse = gl.getUniformLocation(program, 'u_mouse')

    let mouseX = 0, mouseY = 0
    const onMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX
      mouseY = canvas.height - e.clientY
    }
    window.addEventListener('mousemove', onMouseMove)

    let startTime = performance.now()
    let animId: number

    const render = () => {
      const elapsed = (performance.now() - startTime) / 1000
      gl.uniform1f(uTime, elapsed)
      gl.uniform2f(uResolution, canvas.width, canvas.height)
      gl.uniform2f(uMouse, mouseX, mouseY)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
      animId = requestAnimationFrame(render)
    }
    animId = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMouseMove)
      gl.deleteProgram(program)
      gl.deleteShader(vs)
      gl.deleteShader(fs)
      gl.deleteBuffer(buffer)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ display: 'block' }}
    />
  )
}
