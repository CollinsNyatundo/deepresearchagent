import functionPlot from 'function-plot'

export function renderFunctionPlot(
  element: HTMLElement,
  functions: { fn: string; color?: string }[]
): void {
  functionPlot({
    target: element,
    width: 400,
    height: 300,
    xAxis: { domain: [-10, 10] },
    yAxis: { domain: [-10, 10] },
    grid: true,
    data: functions.map((f) => ({ fn: f.fn, color: f.color || '#3a7bd5' })),
  })
}
