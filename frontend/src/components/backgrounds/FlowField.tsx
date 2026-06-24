import { useEffect, useRef } from 'react'

export default function FlowField() {
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

    const vsSource = `
      attribute vec2 a_position;
      void main() {
        gl_Position = vec4(a_position, 0.0, 1.0);
      }
    `

    const fsSource = `
      precision highp float;
      uniform float u_time;
      uniform vec2 u_resolution;
      uniform vec2 u_mouse;

      #define PI 3.14159265359

      vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
      vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
      vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

      float snoise(vec2 v) {
        const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                           -0.577350269189626, 0.024390243902439);
        vec2 i  = floor(v + dot(v, C.yy));
        vec2 x0 = v -   i + dot(i, C.xx);
        vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
        vec4 x12 = x0.xyxy + C.xxzz;
        x12.xy -= i1;
        i = mod289(i);
        vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                                 + i.x + vec3(0.0, i1.x, 1.0));
        vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
        m = m*m; m = m*m;
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

      float fbm(vec2 p) {
        float v = 0.0, a = 0.5;
        for (int i = 0; i < 5; i++) {
          v += a * snoise(p);
          p *= 2.03;
          a *= 0.5;
        }
        return v;
      }

      // Domain warping for fabric folds
      vec2 warp(vec2 p, float t) {
        float n1 = fbm(p * 1.5 + t * 0.1);
        float n2 = fbm(p * 1.5 + vec2(5.2, 1.3) + t * 0.08);
        return p + vec2(n1, n2) * 0.3;
      }

      // Kajiya-Kay anisotropic specular
      float anisoSpecular(vec2 uv, vec2 lightDir, vec2 viewDir) {
        vec2 wp = warp(uv, u_time * 0.2);
        vec2 fabricDir = normalize(vec2(
          fbm(wp * 2.0 + vec2(0.0, 1.0)) - fbm(wp * 2.0 + vec2(0.0, -1.0)),
          fbm(wp * 2.0 + vec2(1.0, 0.0)) - fbm(wp * 2.0 + vec2(-1.0, 0.0))
        ));
        float halfDot = dot(normalize(lightDir + viewDir), fabricDir);
        return pow(max(halfDot, 0.0), 32.0) * 0.5;
      }

      // ACES tone mapping
      vec3 acesToneMap(vec3 x) {
        float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
        return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
      }

      void main() {
        vec2 uv = gl_FragCoord.xy / u_resolution;
        vec2 aspect = vec2(u_resolution.x / u_resolution.y, 1.0);
        vec2 p = uv * aspect;
        float t = u_time * 0.15;

        // Mouse-controlled light direction
        vec2 mouseNorm = u_mouse / u_resolution;
        vec2 lightDir = normalize(vec2(
          (mouseNorm.x - 0.5) * 2.0,
          (mouseNorm.y - 0.5) * 2.0 + 0.5
        ));
        vec2 viewDir = vec2(0.0, 1.0);

        // 3-layer silk simulation
        float silk1 = anisoSpecular(p * 2.0, lightDir, viewDir);
        float silk2 = anisoSpecular(p * 3.0 + vec2(1.0, 0.5), lightDir * 0.8, viewDir) * 0.6;
        float silk3 = anisoSpecular(p * 1.5 + vec2(0.5, 1.0), lightDir * 1.2, viewDir) * 0.4;
        float silk = silk1 + silk2 + silk3;

        // Base color with domain warping
        vec2 wp = warp(p, t);
        float baseNoise = fbm(wp * 0.8 + t * 0.05) * 0.5 + 0.5;
        vec3 baseColor = mix(vec3(0.08, 0.06, 0.05), vec3(0.15, 0.12, 0.10), baseNoise);

        // Add specular highlights
        vec3 highlight = vec3(0.85, 0.80, 0.75) * silk * 0.8;
        vec3 color = baseColor + highlight;

        // Film grain
        float grain = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) * 0.04 - 0.02;
        color += grain;

        // ACES tone mapping + gamma correction
        color = acesToneMap(color);
        color = pow(color, vec3(1.0 / 2.2));

        // Desaturate to grayscale
        float gray = dot(color, vec3(0.299, 0.587, 0.114));
        color = vec3(gray);

        gl_FragColor = vec4(color, 1.0);
      }
    `

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
