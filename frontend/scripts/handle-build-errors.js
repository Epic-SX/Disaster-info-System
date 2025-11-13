// Handle unhandled promise rejections during build
process.on('unhandledRejection', (reason, promise) => {
  console.warn('Unhandled Promise Rejection during build:', reason);
  // Don't exit the process during build
});

process.on('uncaughtException', (error) => {
  console.warn('Uncaught Exception during build:', error);
  // Don't exit the process during build
});

// Export empty object to make this a valid module
module.exports = {};


