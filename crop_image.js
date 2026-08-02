const fs = require('fs');
// Let's not over-engineer the image if it's already an okay size, but since it is 332x336 which is almost a square, we will let it be. If the browser scales it, it will look fine. 
// 
// If it's too high up, we would need to center it. It's an arch shape with empty space at the bottom.
// We can use macOS sips to pad the image to square if we wanted, e.g. sips -p 336 336
