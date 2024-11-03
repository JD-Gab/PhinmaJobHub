$(document).ready(function() {
function toggleIcon(jobId) {
    const anchor = document.getElementById('myAnchor');
    const icon = anchor.querySelector('i');
    const alertBox = document.getElementById('myAlert');

    console.log("Received parameters:", jobId);

    //const jobId = jobIdindex[0];
    
    //const jobs = [123, 456, 789];
    //const jobId = jobs[0];
  
    // Toggle the icon class (e.g., from plus to minus)
    icon.classList.toggle('bi-heart');
    icon.classList.toggle('bi-heart-fill');

    if (icon.classList.contains('bi-heart-fill')) {
        alertBox.innerHTML = 'Job post saved!';
    } else {
        alertBox.innerHTML = 'Job post unsaved.';
    }

    // Show or hide the alert
    alertBox.style.display = 'block';
    setTimeout(() => {
        alertBox.style.display = 'none';
    }, 3000); // Hide after 3 seconds

    $.ajax({
        url: '/bookmark', // Your Flask route URL
        type: 'POST',
        data:  { jobId }, // Send the jobId as data
        success: function(response) {
            // Handle the response from Flask (if needed)
            console.log('Response from Flask:', response);
        },
        error: function(error) {
            console.error('Error sending data to Flask:', error);
        }
    });



  }

  document.getElementById('myAnchor').addEventListener('click', toggleIcon);
});
