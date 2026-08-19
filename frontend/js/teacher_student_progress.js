 // Overall class performance (Bar Chart)
  new Chart(document.getElementById('overallChart'), {
    type: 'bar',
    data: {
      labels: ['Physics', 'Chemistry','Mathematics', 'Biology', 'Computer', 'English'],
      datasets: [{
        label: 'Average Score',
        data: [85, 80, 95, 90,95,88],
        backgroundColor: ['#5A77DF','#5A77DF','#5A77DF','#5A77DF'],
        borderRadius: 20,
        hoverBackgroundColor: '#3E53A0'
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, max:100 } }
    }
  });

  // Attendance trend (Line Chart)
  
  new Chart(document.getElementById('attendanceChart'), {
    type: 'line',
    data: {
      labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
      datasets: [{
        label: 'Attendance %',
        data: [92,95,90,96],
        borderColor: '#5A77DF',
        fill: true,
        backgroundColor: 'rgba(90, 119, 223, 0.1)',
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: {min: 10, stepSize:10, max:100 } }
    }
  });

  // Animate circular rings (reads data-target attribute)
  
document.addEventListener('DOMContentLoaded', () => {
  // Get CSS --primary variable or fallback color
  const primaryColor = (getComputedStyle(document.documentElement).getPropertyValue('--primary') || '#5A77DF').trim() || '#5A77DF';

  document.querySelectorAll('.ring').forEach(ring => {
    const target = parseInt(ring.dataset.target, 10) || 0;
    const innerValue = ring.querySelector('.ring-value');
    let current = 0;
    const speed = 8; // lower = faster

    const step = () => {
      current++;
      innerValue.textContent = current + '%';
      ring.style.background = `conic-gradient(${primaryColor} ${current}%, #CCD4DE ${current}%)`;
      if (current < target) {
        requestAnimationFrame(() => setTimeout(step, speed));
      } else {
        innerValue.textContent = target + '%';
        ring.style.background = `conic-gradient(${primaryColor} ${target}%, #CCD4DE ${target}%)`;
      }
    };

    setTimeout(step, 200);
  });
});
